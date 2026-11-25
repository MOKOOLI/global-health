from __future__ import annotations

import statistics
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from . import analytics as A
from . import llm
from .db import get_db
from .insights import analyze
from .measures import (
    CATEGORIES,
    DATA_QUALITY,
    DISCLAIMER_EN,
    DISCLAIMER_FA,
    MEASURES,
    SEX_LABELS,
    UNITS,
)
from .models import Country, Disease, Indicator, Observation, OutbreakAlert, Source
from .queries import (
    disease_dict,
    get_indicator,
    has_synthetic,
    indicator_dict,
    latest_year,
    series,
    year_slice,
    years_available,
)

router = APIRouter(prefix="/api")

MEASURE_PREF = {"incidence": 0, "prevalence": 1, "mortality": 2, "deaths": 3, "cases": 4,
                "daly": 5, "coverage": 6}
UNIT_PREF = {"per_100k": 0, "per_1000": 1, "percent": 2, "count": 3}


def _pref(ind: Indicator):
    return (UNIT_PREF.get(ind.unit, 9), MEASURE_PREF.get(ind.measure, 9), ind.source.is_synthetic)


def country_name(c: Country, lang: str) -> str:
    return (c.name_fa or c.name_en) if lang == "fa" else c.name_en


def _ind_or_404(db: Session, code: str) -> Indicator:
    ind = db.scalar(
        select(Indicator)
        .options(joinedload(Indicator.source), joinedload(Indicator.disease))
        .where(Indicator.code == code)
    )
    if ind is None:
        raise HTTPException(404, f"Unknown indicator {code}")
    return ind


# --------------------------------------------------------------------------------------- meta
@router.get("/health")
def health(db: Session = Depends(get_db)):
    n = db.scalar(select(func.count()).select_from(Observation))
    return {"status": "ok", "observations": n, "time": datetime.utcnow().isoformat()}


@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    sources = [
        dict(code=s.code, name=s.name, url=s.url, license=s.license, citation=s.citation,
             is_synthetic=s.is_synthetic)
        for s in db.scalars(select(Source))
    ]
    return dict(
        measures=MEASURES, units=UNITS, data_quality=DATA_QUALITY, categories=CATEGORIES,
        sexes=SEX_LABELS, disclaimer=dict(en=DISCLAIMER_EN, fa=DISCLAIMER_FA), sources=sources,
        has_synthetic=has_synthetic(db),
        counts=dict(
            countries=db.scalar(select(func.count()).select_from(Country)),
            diseases=db.scalar(select(func.count()).select_from(Disease)),
            indicators=db.scalar(select(func.count()).select_from(Indicator)),
            observations=db.scalar(select(func.count()).select_from(Observation)),
        ),
    )


@router.get("/countries")
def countries(q: str | None = None, lang: str = "en", db: Session = Depends(get_db)):
    stmt = select(Country).order_by(Country.name_en)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Country.name_en.ilike(like), Country.name_fa.like(like),
                              Country.iso3.ilike(like)))
    return [
        dict(iso3=c.iso3, iso2=c.iso2, iso_numeric=c.iso_numeric, name=country_name(c, lang),
             name_en=c.name_en, name_fa=c.name_fa, region=c.region,
             income_group=c.income_group, population=c.population)
        for c in db.scalars(stmt)
    ]


@router.get("/diseases")
def diseases(category: str | None = None, q: str | None = None, only_with_data: bool = False,
             lang: str = "en", db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Indicator.disease_id, func.count()).group_by(Indicator.disease_id)).all())
    stmt = select(Disease).order_by(Disease.name_en)
    if category:
        stmt = stmt.where(Disease.category == category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Disease.name_en.ilike(like), Disease.name_fa.like(like),
                              Disease.icd10.ilike(like), Disease.slug.ilike(like)))
    out = []
    for d in db.scalars(stmt):
        n = counts.get(d.id, 0)
        if only_with_data and not n:
            continue
        out.append({**disease_dict(d, lang), "indicator_count": n})
    return out


@router.get("/diseases/{slug}")
def disease_detail(slug: str, lang: str = "en", db: Session = Depends(get_db)):
    d = db.scalar(select(Disease).where(Disease.slug == slug))
    if d is None:
        raise HTTPException(404, "Unknown disease")
    inds = list(db.scalars(
        select(Indicator).options(joinedload(Indicator.source)).where(Indicator.disease_id == d.id)
    ))
    inds.sort(key=_pref)
    items = []
    for i in inds:
        ly = latest_year(db, i.id)
        n = db.scalar(select(func.count(func.distinct(Observation.country_iso3)))
                      .where(Observation.indicator_id == i.id)) or 0
        items.append({**indicator_dict(i, lang), "latest_year": ly, "n_countries": n})
    return dict(**disease_dict(d, lang), indicators=items,
                default_indicator=items[0]["code"] if items else None)


# ---------------------------------------------------------------------------- indicator data
@router.get("/indicators/{code}/map")
def indicator_map(code: str, year: int | None = None, sex: str = "ALL", age: str = "ALL",
                  lang: str = "en", db: Session = Depends(get_db)):
    ind = _ind_or_404(db, code)
    years = years_available(db, ind.id, sex, age)
    if not years:
        raise HTTPException(404, "No data for this selection")
    yr = year if year in years else years[-1]
    rows = year_slice(db, ind.id, yr, sex, age)
    data = [
        dict(iso3=c.iso3, iso_numeric=c.iso_numeric, name=country_name(c, lang), value=o.value,
             low=o.low, high=o.high, quality=o.data_quality, region=c.region)
        for o, c in rows
    ]
    vals = [r["value"] for r in data]
    sexes = sorted(set(db.scalars(select(Observation.sex).where(Observation.indicator_id == ind.id).distinct())))
    ages = sorted(set(db.scalars(select(Observation.age_group).where(Observation.indicator_id == ind.id).distinct())))
    covered = {c.iso3: c.population for _, c in rows}
    all_c = list(db.execute(select(Country.iso3, Country.population)))
    with_pop = [(i, p) for i, p in all_c if p]
    pop_share = None                       # only when most countries have a population, else the share would mislead
    if len(with_pop) >= 0.6 * len(all_c):
        tot = sum(p for _, p in with_pop)
        pop_share = round(sum(p for i, p in with_pop if i in covered) / tot, 4) if tot else None
    return dict(indicator=indicator_dict(ind, lang), year=yr, years=years, sexes=sexes,
                age_groups=ages, breaks=A.quantiles(vals), min=min(vals), max=max(vals),
                n=len(vals), n_total=len(all_c), population_share=pop_share, data=data)


@router.get("/indicators/{code}/trend")
def indicator_trend(code: str, countries: str = Query(..., description="comma-separated ISO3"),
                    sex: str = "ALL", age: str = "ALL", forecast: bool = False, lang: str = "en",
                    db: Session = Depends(get_db)):
    ind = _ind_or_404(db, code)
    isos = [c.strip().upper() for c in countries.split(",") if c.strip()][:8]
    out = []
    for iso in isos:
        c = db.get(Country, iso)
        if c is None:
            continue
        obs = series(db, ind.id, iso, sex, age)
        item = dict(
            iso3=iso, name=country_name(c, lang),
            points=[dict(year=o.year, value=o.value, low=o.low, high=o.high, quality=o.data_quality)
                    for o in obs],
        )
        out.append(item)
    if forecast and len(out) == 1 and out[0]["points"]:
        pts = out[0]["points"]
        out[0]["forecast"] = A.forecast_holt([p["year"] for p in pts], [p["value"] for p in pts])
    return dict(indicator=indicator_dict(ind, lang), series=out)


@router.get("/indicators/{code}/ranking")
def indicator_ranking(code: str, year: int | None = None, sex: str = "ALL", age: str = "ALL",
                      order: str = "desc", limit: int = Query(25, le=300), region: str | None = None,
                      lang: str = "en", db: Session = Depends(get_db)):
    ind = _ind_or_404(db, code)
    yr = year or latest_year(db, ind.id, sex, age)
    if yr is None:
        raise HTTPException(404, "No data")
    rows = year_slice(db, ind.id, yr, sex, age)
    rows.sort(key=lambda r: r[0].value, reverse=(order != "asc"))
    ranked = [(i + 1, o, c) for i, (o, c) in enumerate(rows)]
    if region:
        ranked = [t for t in ranked if t[2].region == region]
    return dict(
        indicator=indicator_dict(ind, lang), year=yr, n=len(rows),
        rows=[dict(rank=r, iso3=c.iso3, name=country_name(c, lang), region=c.region,
                   value=o.value, low=o.low, high=o.high, quality=o.data_quality)
              for r, o, c in ranked[:limit]],
    )


# ------------------------------------------------------------------------------- country view
@router.get("/countries/{iso3}/profile")
def country_profile(iso3: str, measure: str | None = None, lang: str = "en",
                    db: Session = Depends(get_db)):
    """For one country: every disease with data, ranked by how far it exceeds the global median.

    Useful for travel/migrant medicine ("what is more common there than elsewhere?").
    Only per-capita indicators are compared (counts depend on population size).
    """
    c = db.get(Country, iso3.upper())
    if c is None:
        raise HTTPException(404, "Unknown country")
    inds = list(db.scalars(
        select(Indicator).options(joinedload(Indicator.source), joinedload(Indicator.disease))
        .where(Indicator.disease_id.is_not(None))
    ))
    best: dict[int, Indicator] = {}
    for i in sorted(inds, key=_pref):
        if measure and i.measure != measure:
            continue
        best.setdefault(i.disease_id, i)
    items = []
    for ind in best.values():
        yr = latest_year(db, ind.id)
        if yr is None:
            continue
        mine = db.scalar(select(Observation).where(
            Observation.indicator_id == ind.id, Observation.country_iso3 == c.iso3,
            Observation.year == yr, Observation.sex == "ALL", Observation.age_group == "ALL"))
        if mine is None:
            continue
        item = dict(
            disease=disease_dict(ind.disease, lang), indicator=ind.code, measure=ind.measure,
            unit=ind.unit, year=yr, value=mine.value, low=mine.low, high=mine.high,
            quality=mine.data_quality, synthetic=ind.source.is_synthetic,
            higher_is_worse=ind.higher_is_worse,
            source=dict(code=ind.source.code, name=ind.source.name, license=ind.source.license),
        )
        if ind.unit != "count":
            vals = list(db.scalars(select(Observation.value).where(
                Observation.indicator_id == ind.id, Observation.year == yr,
                Observation.sex == "ALL", Observation.age_group == "ALL")))
            if len(vals) >= 20:
                med = statistics.median(vals)
                item.update(global_median=med,
                            ratio_to_median=(mine.value / med) if med else None,
                            rank=1 + sum(1 for v in vals if v > mine.value), n=len(vals))
        items.append(item)
    items.sort(key=lambda x: -(x.get("ratio_to_median") or 0))
    return dict(country=dict(iso3=c.iso3, name=country_name(c, lang), region=c.region,
                             income_group=c.income_group, population=c.population),
                items=items, generated=date.today().isoformat())


# ---------------------------------------------------------------------------------- insights
@router.get("/insights")
async def insights(indicator: str, country: str, sex: str = "ALL", age: str = "ALL",
                   lang: str = "en", narrate: bool = False, db: Session = Depends(get_db)):
    ind = _ind_or_404(db, indicator)
    c = db.get(Country, country.upper())
    if c is None:
        raise HTTPException(404, "Unknown country")
    res = analyze(db, ind, c, sex, age)
    out = dict(
        indicator=indicator_dict(ind, lang),
        country=dict(iso3=c.iso3, name=country_name(c, lang)),
        findings=res["findings"], facts=res["facts"], points=res["points"],
        disclaimer=DISCLAIMER_FA if lang == "fa" else DISCLAIMER_EN,
        synthetic=ind.source.is_synthetic,
    )
    if narrate and res["findings"]:
        out["narrative"] = await llm.narrate(res["findings"], lang)
    return out


# ------------------------------------------------------------------------- search & alerts
@router.get("/search")
def search(q: str = Query(..., min_length=1), lang: str = "en", db: Session = Depends(get_db)):
    like = f"%{q}%"
    ds = db.scalars(select(Disease).where(or_(
        Disease.name_en.ilike(like), Disease.name_fa.like(like), Disease.icd10.ilike(like),
        Disease.slug.ilike(like))).limit(15))
    cs = db.scalars(select(Country).where(or_(
        Country.name_en.ilike(like), Country.name_fa.like(like), Country.iso3.ilike(like))).limit(10))
    return dict(diseases=[disease_dict(d, lang) for d in ds],
                countries=[dict(iso3=c.iso3, name=country_name(c, lang)) for c in cs])


@router.get("/alerts")
def alerts(country: str | None = None, disease: str | None = None, limit: int = Query(30, le=100),
           db: Session = Depends(get_db)):
    stmt = select(OutbreakAlert).order_by(OutbreakAlert.published_at.desc()).limit(limit)
    if country:
        stmt = stmt.where(OutbreakAlert.country_iso3 == country.upper())
    if disease:
        d = db.scalar(select(Disease).where(Disease.slug == disease))
        stmt = stmt.where(OutbreakAlert.disease_id == (d.id if d else -1))
    return [dict(title=a.title, url=a.url, source=a.source, published_at=a.published_at,
                 country_iso3=a.country_iso3, summary=a.summary) for a in db.scalars(stmt)]
