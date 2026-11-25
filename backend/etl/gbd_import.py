"""Import a CSV exported from the IHME GBD Results tool (https://vizhub.healthdata.org/gbd-results/).

This is the backbone for full "all countries x all diseases" coverage. IHME does not offer a
public bulk API, so the workflow is:

  1. In GBD Results choose: Measure = Incidence, Prevalence, Deaths, DALYs;
     Metric = Rate (and Number); Cause = the causes in catalogue.py; Location = countries;
     Age = All ages + Age-standardized; Sex = Both/Male/Female; Years = all.
  2. Download the CSV(s) (check IHME's current licence terms and cite them).
  3. python -m etl.run gbd path/to/file.csv

Expected columns: measure_name, location_name, sex_name, age_name, cause_name, metric_name,
year, val, upper, lower.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pycountry
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Disease
from etl.common import Run, get_or_create_source, upsert_indicator, upsert_observations

# GBD location names that differ from ISO names.
ALIASES = {
    "russia": "RUS", "iran": "IRN", "vietnam": "VNM", "south korea": "KOR", "north korea": "PRK",
    "turkey": "TUR", "turkiye": "TUR", "syria": "SYR", "laos": "LAO", "bolivia": "BOL",
    "venezuela": "VEN", "tanzania": "TZA", "moldova": "MDA", "brunei": "BRN", "cape verde": "CPV",
    "cote d'ivoire": "CIV", "the gambia": "GMB", "the bahamas": "BHS", "taiwan (province of china)": "TWN",
    "micronesia (federated states of)": "FSM", "congo": "COG", "democratic republic of the congo": "COD",
    "palestine": "PSE", "state of palestine": "PSE", "czechia": "CZE", "eswatini": "SWZ",
    "timor-leste": "TLS", "united states of america": "USA", "united kingdom": "GBR",
    "macedonia": "MKD", "north macedonia": "MKD", "kosovo": "XKX",
}

MEASURES = {
    "incidence": "incidence",
    "prevalence": "prevalence",
    "deaths": "deaths",
    "dalys": "daly",
    "dalys (disability-adjusted life years)": "daly",
}
SEX = {"both": "ALL", "male": "M", "female": "F"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9' ()-]+", "", s).strip()


def _build_country_lookup(db: Session) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for c in db.scalars(select(Country)):
        lookup[_norm(c.name_en)] = c.iso3
    for pc in pycountry.countries:
        lookup.setdefault(_norm(pc.name), pc.alpha_3)
        if hasattr(pc, "official_name"):
            lookup.setdefault(_norm(pc.official_name), pc.alpha_3)
    lookup.update({k: v for k, v in ALIASES.items()})
    return lookup


def _age(name: str) -> str:
    n = name.strip().lower()
    if n in ("all ages", "all age"):
        return "ALL"
    if n.startswith("age-standardized") or n.startswith("age-standardised"):
        return "ASR"
    return re.sub(r"\s+", "", name)[:24]


def import_gbd_csv(db: Session, path: str) -> dict:
    src = get_or_create_source(db, "GBD")
    diseases = list(db.scalars(select(Disease)))
    cause_to_disease = {}
    for d in diseases:
        for cause in (d.gbd_causes or "").split("|"):
            if cause:
                cause_to_disease[_norm(cause)] = d
    countries = _build_country_lookup(db)

    groups: dict[tuple, list[dict]] = defaultdict(list)
    skipped = defaultdict(int)
    with open(Path(path), newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            disease = cause_to_disease.get(_norm(r["cause_name"]))
            if disease is None:
                skipped["unknown_cause"] += 1
                continue
            iso3 = countries.get(_norm(r["location_name"]))
            if iso3 is None:
                skipped["unknown_location"] += 1  # sub-national units, regions, etc.
                continue
            measure = MEASURES.get(r["measure_name"].strip().lower())
            if measure is None:
                skipped["unknown_measure"] += 1
                continue
            metric = r["metric_name"].strip().lower()
            if metric == "rate":
                unit = "per_100k"
                if measure == "deaths":
                    measure = "mortality"
            elif metric == "number":
                unit = "count"
            elif metric == "percent":
                unit = "percent"
            else:
                skipped["unknown_metric"] += 1
                continue
            age = _age(r["age_name"])
            groups[(disease.id, disease.slug, measure, unit)].append(
                dict(
                    country_iso3=iso3,
                    year=int(r["year"]),
                    sex=SEX.get(r["sex_name"].strip().lower(), "ALL"),
                    age_group=age,
                    value=float(r["val"]),
                    low=float(r["lower"]) if r.get("lower") not in (None, "") else None,
                    high=float(r["upper"]) if r.get("upper") not in (None, "") else None,
                    data_quality="modeled",
                )
            )

    loaded = 0
    with Run(db, "gbd_import") as run:
        for (disease_id, slug, measure, unit), rows in groups.items():
            ind = upsert_indicator(
                db,
                f"gbd-{slug}-{measure}-{unit}",
                disease_id=disease_id,
                source_id=src.id,
                measure=measure,
                unit=unit,
                name_en=f"{slug.replace('-', ' ').title()} - {measure} ({unit.replace('_', ' ')}), GBD",
                higher_is_worse=True,
            )
            n = upsert_observations(db, ind.id, rows)
            loaded += n
            run.rows += n
        db.commit()
    return {"indicators": len(groups), "rows": loaded, "skipped": dict(skipped)}
