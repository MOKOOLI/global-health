"""Weekly surveillance connectors.

Every connector has two layers:
  parse_*()  pure function: raw text/JSON -> {iso3: {week_start: value}}   (unit-tested on fixtures)
  load_*()   fetches + calls write_weekly()

Verification status (honest):
  jhu_covid, owid_mpox  - run against the real GitHub files (the only hosts reachable while building)
  who_covid, delphi_fluview, cdc_socrata, csv_weekly - written from the providers' published schemas,
        validated by fixtures, NOT yet run against the live endpoints. They fail loudly with the
        columns/values they found instead of loading guesses.
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

import httpx
import pycountry
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Disease, SurveillanceSeries, SurveillanceWeekly
from etl.common import USER_AGENT, Run, get_or_create_source
from etl.gbd_import import ALIASES, _norm

Weekly = dict[str, dict[date, float]]  # iso3 -> {week_start: value}

JHU_URL = ("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/"
           "csse_covid_19_time_series/time_series_covid19_confirmed_global.csv")
OWID_MPOX_URL = "https://raw.githubusercontent.com/owid/monkeypox/main/owid-monkeypox-data.csv"
WHO_COVID_URL = "https://srhdpeuwpubsa.blob.core.windows.net/whdh/COVID/WHO-COVID-19-global-data.csv"
DELPHI_URL = "https://api.delphi.cmu.edu/epidata/fluview/"  # legacy V3 path; Delphi is migrating to V5
SOCRATA_BASE = "https://data.cdc.gov/resource"

SOURCE_DEFS = {
    "JHU_CSSE": dict(
        name="Johns Hopkins CSSE COVID-19 Data Repository (archived 2023-03-10)",
        url="https://github.com/CSSEGISandData/COVID-19", license="CC BY 4.0",
        citation="Dong E, Du H, Gardner L. An interactive web-based dashboard to track COVID-19 in real time. "
                 "Lancet Infect Dis 2020.",
    ),
    "OWID_MPOX": dict(
        name="Our World in Data - Mpox (aggregating WHO and national reports)",
        url="https://github.com/owid/monkeypox", license="CC BY 4.0 (check repository)",
        citation="Mathieu E, et al. Mpox (monkeypox). Our World in Data.",
    ),
    "WHO_COVID": dict(
        name="WHO COVID-19 global data", url="https://data.who.int/dashboards/covid19/data",
        license="CC BY-4.0 (check WHO terms)", citation="World Health Organization. COVID-19 dashboard.",
    ),
    "CDC_NNDSS": dict(
        name="CDC NNDSS Weekly Data (data.cdc.gov x9gk-5huc)", url="https://data.cdc.gov/d/x9gk-5huc",
        license="U.S. Government work (verify dataset licence)",
        citation="Centers for Disease Control and Prevention. National Notifiable Diseases Surveillance System.",
    ),
    "CDC_FLUVIEW": dict(
        name="CDC FluView ILINet via Delphi Epidata", url="https://cmu-delphi.github.io/delphi-epidata/api/fluview.html",
        license="See Delphi Epidata terms", citation="Carnegie Mellon Delphi Group. Delphi Epidata API; CDC FluView.",
    ),
    "CSV_WEEKLY": dict(name="Custom weekly CSV feed (user supplied)", url=None, license="per feed", citation=None),
}


# ------------------------------------------------------------------------ helpers
def http_text(url: str, params: dict | None = None, timeout: float = 180.0) -> str:
    r = httpx.get(url, params=params, timeout=timeout, follow_redirects=True,
                  headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.text


def read_source(src: str) -> str:
    if re.match(r"^https?://", src):
        return http_text(src)
    with open(src, encoding="utf-8-sig") as f:
        return f.read()


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def to_weeks(daily: dict[date, float], min_days: int = 7) -> dict[date, float]:
    """Sum daily values into Monday-start weeks. Weeks with fewer than `min_days` observed days and
    the final (still incomplete) week are dropped so a partial week never looks like a collapse."""
    if not daily:
        return {}
    last = max(daily)
    groups: dict[date, list[float]] = defaultdict(list)
    for d, v in daily.items():
        groups[monday(d)].append(v)
    return {w: float(sum(vs)) for w, vs in groups.items() if len(vs) >= min_days and w + timedelta(days=6) <= last}


def mmwr_week_start(year: int, week: int) -> date:
    """First day (Sunday) of MMWR epidemiological week `week` of `year`."""
    jan1 = date(year, 1, 1)
    dow = (jan1.weekday() + 1) % 7  # Sunday = 0
    first = jan1 - timedelta(days=dow) if dow <= 3 else jan1 + timedelta(days=7 - dow)
    return first + timedelta(days=7 * (week - 1))


JHU_ALIASES = {
    "us": "USA", "korea, south": "KOR", "taiwan*": "TWN", "burma": "MMR", "congo (kinshasa)": "COD",
    "congo (brazzaville)": "COG", "cote d'ivoire": "CIV", "west bank and gaza": "PSE", "holy see": "VAT",
    "cabo verde": "CPV", "kosovo": "XKX", "czechia": "CZE", "russia": "RUS", "iran": "IRN", "syria": "SYR",
    "vietnam": "VNM", "laos": "LAO", "brunei": "BRN", "bolivia": "BOL", "venezuela": "VEN",
    "tanzania": "TZA", "moldova": "MDA", "eswatini": "SWZ", "timor-leste": "TLS", "north macedonia": "MKD",
    "micronesia": "FSM", "the bahamas": "BHS", "gambia, the": "GMB", "bahamas, the": "BHS",
}
JHU_SKIP = {"diamond princess", "ms zaandam", "summer olympics 2020", "winter olympics 2022"}


def country_lookup(db: Session) -> dict[str, str]:
    lk: dict[str, str] = {}
    for c in db.scalars(select(Country)):
        lk[_norm(c.name_en)] = c.iso3
    for pc in pycountry.countries:
        lk.setdefault(_norm(pc.name), pc.alpha_3)
        if hasattr(pc, "official_name"):
            lk.setdefault(_norm(pc.official_name), pc.alpha_3)
    lk.update({_norm(k): v for k, v in ALIASES.items()})
    lk.update({_norm(k): v for k, v in JHU_ALIASES.items()})
    lk.update({"korea north": "PRK", "korea south": "KOR"})
    return lk


def iso2_to_iso3(db: Session) -> dict[str, str]:
    return {c.iso2: c.iso3 for c in db.scalars(select(Country)) if c.iso2}


# ------------------------------------------------------------------------ writer
def write_weekly(
    db: Session, disease_slug: str, source_code: str, data: Weekly, *, metric: str = "new_cases",
    unit: str = "count", note: str | None = None, job: str = "surveillance",
) -> dict:
    disease = db.scalar(select(Disease).where(Disease.slug == disease_slug))
    if disease is None:
        raise ValueError(f"unknown disease slug {disease_slug!r}; run `etl.run reference` first")
    src = get_or_create_source(db, source_code, **SOURCE_DEFS.get(source_code, dict(name=source_code)))
    known = set(db.scalars(select(Country.iso3)))
    n_rows = n_series = 0
    skipped = []
    with Run(db, job) as run:
        for iso3, weeks in data.items():
            if iso3 not in known:
                skipped.append(iso3)
                continue
            if not weeks:
                continue
            s = db.scalar(select(SurveillanceSeries).where(
                SurveillanceSeries.disease_id == disease.id, SurveillanceSeries.country_iso3 == iso3,
                SurveillanceSeries.source_id == src.id, SurveillanceSeries.metric == metric))
            if s is None:
                s = SurveillanceSeries(disease_id=disease.id, country_iso3=iso3, source_id=src.id,
                                       metric=metric, unit=unit, note=note)
                db.add(s)
                db.flush()
            existing = {w.week_start: w for w in db.scalars(
                select(SurveillanceWeekly).where(SurveillanceWeekly.series_id == s.id))}
            new = []
            for wk, v in weeks.items():
                row = existing.get(wk)
                if row is not None:
                    row.value = float(v)
                else:
                    new.append(dict(series_id=s.id, week_start=wk, value=float(v)))
            if new:
                db.bulk_insert_mappings(SurveillanceWeekly, new)
            n_rows += len(weeks)
            n_series += 1
        run.rows = n_rows
    return dict(series=n_series, rows=n_rows, skipped_unknown_countries=sorted(set(skipped))[:20])


# ------------------------------------------------------------------------ JHU COVID (cumulative -> weekly)
def parse_jhu_confirmed(text: str, lookup: dict[str, str]) -> tuple[Weekly, list[str]]:
    rd = csv.reader(io.StringIO(text))
    header = next(rd)
    if header[:2] != ["Province/State", "Country/Region"] or len(header) < 10:
        raise ValueError(f"unexpected JHU header: {header[:6]}")
    dates = [datetime.strptime(h, "%m/%d/%y").date() for h in header[4:]]
    cum: dict[str, list[float]] = {}
    unmatched: set[str] = set()
    for row in rd:
        name = row[1].strip()
        if _norm(name) in JHU_SKIP:
            continue
        iso3 = lookup.get(_norm(name))
        if iso3 is None:
            unmatched.add(name)
            continue
        vals = [float(x) if x not in ("", None) else 0.0 for x in row[4:]]
        acc = cum.setdefault(iso3, [0.0] * len(dates))
        for i, v in enumerate(vals):
            acc[i] += v
    out: Weekly = {}
    for iso3, c in cum.items():
        daily = {dates[0]: max(c[0], 0.0)}
        for i in range(1, len(dates)):
            daily[dates[i]] = max(c[i] - c[i - 1], 0.0)  # corrections can make increments negative
        out[iso3] = to_weeks(daily)
    return out, sorted(unmatched)


def load_jhu_covid(db: Session, source: str = JHU_URL) -> dict:
    data, unmatched = parse_jhu_confirmed(read_source(source), country_lookup(db))
    res = write_weekly(db, "covid-19", "JHU_CSSE", data, metric="new_cases", job="surv_jhu_covid",
                       note="Confirmed cases (testing-dependent); JHU archive ends 2023-03-10")
    res["unmatched_names"] = unmatched
    return res


# ------------------------------------------------------------------------ OWID mpox
def parse_owid_mpox(text: str, valid_iso3: set[str]) -> Weekly:
    rd = csv.DictReader(io.StringIO(text))
    need = {"date", "iso_code", "new_cases"}
    if not need <= set(rd.fieldnames or []):
        raise ValueError(f"unexpected OWID columns: {rd.fieldnames}")
    daily: dict[str, dict[date, float]] = defaultdict(dict)
    for r in rd:
        iso = r["iso_code"]
        if iso not in valid_iso3 or r["new_cases"] in ("", None):
            continue
        daily[iso][date.fromisoformat(r["date"])] = float(r["new_cases"])
    # reports can be sparse within a week, so accept weeks with >=1 observed day
    return {iso: to_weeks(d, min_days=1) for iso, d in daily.items()}


def load_owid_mpox(db: Session, source: str = OWID_MPOX_URL) -> dict:
    valid = set(db.scalars(select(Country.iso3)))
    return write_weekly(db, "mpox", "OWID_MPOX", parse_owid_mpox(read_source(source), valid),
                        job="surv_owid_mpox", note="Confirmed cases as reported to WHO/national authorities")


# ------------------------------------------------------------------------ WHO COVID (daily or weekly rows)
def parse_who_covid(text: str, iso2: dict[str, str]) -> Weekly:
    rd = csv.DictReader(io.StringIO(text))
    cols = set(rd.fieldnames or [])
    need = {"Date_reported", "Country_code", "New_cases"}
    if not need <= cols:
        raise ValueError(f"unexpected WHO COVID columns: {sorted(cols)}")
    per: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    for r in rd:
        iso3 = iso2.get(r["Country_code"])
        if iso3 is None or r["New_cases"] in ("", None):
            continue
        d = date.fromisoformat(r["Date_reported"][:10])
        per[iso3][monday(d)] += max(float(r["New_cases"]), 0.0)
    return {k: dict(v) for k, v in per.items()}


def load_who_covid(db: Session, source: str = WHO_COVID_URL) -> dict:
    return write_weekly(db, "covid-19", "WHO_COVID", parse_who_covid(read_source(source), iso2_to_iso3(db)),
                        job="surv_who_covid", note="Reported cases per WHO dashboard")


# ------------------------------------------------------------------------ CDC FluView via Delphi
def parse_delphi_fluview(payload: dict, field: str = "wili") -> Weekly:
    if payload.get("result") not in (1,):
        raise ValueError(f"Delphi returned result={payload.get('result')} message={payload.get('message')!r}")
    out: dict[date, float] = {}
    for r in payload.get("epidata", []):
        v = r.get(field)
        if v is None:
            continue
        ew = int(r["epiweek"])
        out[mmwr_week_start(ew // 100, ew % 100)] = float(v)
    return {"USA": out}


def load_delphi_fluview(db: Session, region: str = "nat", first_epiweek: int = 201001, last_epiweek: int | None = None,
                        url: str = DELPHI_URL) -> dict:
    last = last_epiweek or int(datetime.utcnow().strftime("%Y")) * 100 + 53
    payload = json.loads(http_text(url, {"regions": region, "epiweeks": f"{first_epiweek}-{last}"}))
    return write_weekly(db, "influenza", "CDC_FLUVIEW", parse_delphi_fluview(payload), metric="ili_pct",
                        unit="percent", job="surv_delphi_fluview",
                        note="Weighted % of outpatient visits for influenza-like illness (US national)")


# ------------------------------------------------------------------------ CDC / Socrata (NNDSS weekly)
def parse_nndss_rows(rows: list[dict], label: str, geo_values: list[str], country_iso3: str = "USA") -> Weekly:
    """Rows of the NNDSS Weekly Data dataset: states, year, week, label, m1 (current-week count)."""
    if rows:
        need = {"states", "year", "week", "label", "m1"}
        if not need <= set(rows[0]):
            raise ValueError(f"unexpected NNDSS columns: {sorted(rows[0])}")
    acc: dict[date, float] = defaultdict(float)
    geos = {g.lower() for g in geo_values}
    for r in rows:
        if r["label"].strip().lower() != label.lower() or r["states"].strip().lower() not in geos:
            continue
        try:
            v = float(str(r["m1"]).replace(",", ""))
        except ValueError:
            continue  # flags such as "-" or "N" = not reported
        acc[mmwr_week_start(int(r["year"]), int(r["week"]))] += v
    return {country_iso3: dict(acc)}


def socrata_fetch(dataset: str, where: str | None = None, page: int = 50000, select_: str | None = None) -> list[dict]:
    out, offset = [], 0
    while True:
        params = {"$limit": page, "$offset": offset, "$order": ":id"}
        if where:
            params["$where"] = where
        if select_:
            params["$select"] = select_
        chunk = json.loads(http_text(f"{SOCRATA_BASE}/{dataset}.json", params))
        out.extend(chunk)
        if len(chunk) < page:
            return out
        offset += page


def inspect_socrata(dataset: str = "x9gk-5huc") -> dict:
    """Print what is in a dataset so config values (labels / geographies) are chosen from facts."""
    sample = socrata_fetch(dataset, page=2000)[:2000]
    cols = sorted({k for r in sample for k in r})
    distinct = {c: sorted({r.get(c, "") for r in sample})[:40] for c in ("label", "states") if c in cols}
    return dict(columns=cols, distinct_values_in_first_2000_rows=distinct)


def load_cdc_nndss(db: Session, disease_slug: str, label: str, geo_values: list[str], dataset: str = "x9gk-5huc",
                   country_iso3: str = "USA") -> dict:
    rows = socrata_fetch(dataset, where=f"label = '{label.replace(chr(39), chr(39) * 2)}'")
    data = parse_nndss_rows(rows, label, geo_values, country_iso3)
    if not data[country_iso3]:
        raise ValueError(f"no rows for label={label!r} and geographies={geo_values!r}; "
                         f"run `etl.run surv cdc-inspect` to see the real values")
    return write_weekly(db, disease_slug, "CDC_NNDSS", data, job="surv_cdc_nndss",
                        note=f"NNDSS current-week notifications: {label}")


# ------------------------------------------------------------------------ generic CSV feed
def parse_csv_weekly(
    text: str, *, date_col: str, value_col: str, country_col: str, country_kind: str,
    lookup: dict[str, str], iso2: dict[str, str], cumulative: bool = False, date_format: str | None = None,
) -> Weekly:
    """Any long-format CSV (country, date, value): daily or weekly rows, optionally cumulative."""
    rd = csv.DictReader(io.StringIO(text))
    cols = set(rd.fieldnames or [])
    for c in (date_col, value_col, country_col):
        if c not in cols:
            raise ValueError(f"column {c!r} not in CSV; found {sorted(cols)}")
    per: dict[str, dict[date, float]] = defaultdict(dict)
    for r in rd:
        key = r[country_col].strip()
        iso3 = key.upper() if country_kind == "iso3" else iso2.get(key.upper()) if country_kind == "iso2" else lookup.get(_norm(key))
        if not iso3 or r[value_col] in ("", None):
            continue
        d = datetime.strptime(r[date_col], date_format).date() if date_format else date.fromisoformat(r[date_col][:10])
        per[iso3][d] = per[iso3].get(d, 0.0) + float(r[value_col])
    out: Weekly = {}
    for iso3, d in per.items():
        if cumulative:
            days = sorted(d)
            d = {days[i]: max(d[days[i]] - (d[days[i - 1]] if i else 0.0), 0.0) for i in range(len(days))}
        wk: dict[date, float] = defaultdict(float)
        for day, v in d.items():
            wk[monday(day)] += v
        out[iso3] = dict(wk)
    return out


def load_csv_weekly(db: Session, source: str, disease_slug: str, **kw) -> dict:
    data = parse_csv_weekly(read_source(source), lookup=country_lookup(db), iso2=iso2_to_iso3(db), **kw)
    return write_weekly(db, disease_slug, "CSV_WEEKLY", data, job="surv_csv", note=f"from {source[:120]}")
