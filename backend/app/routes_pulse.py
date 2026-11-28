"""Pulse: what is moving now and how fresh every number is.

Three layers with very different clocks, kept apart on purpose:
* weekly surveillance (days to weeks old)   -> early-warning board
* outbreak alerts (days old)                -> WHO Disease Outbreak News
* annual burden estimates (1-3 years old)   -> latest incidence / mortality per indicator

Nothing here is estimated or filled in. Annual figures are never described as "live"; every row carries its
own year and an age class so the reader can tell a weekly count from a three-year-old estimate.
"""
from __future__ import annotations

import statistics
import threading
import time
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from . import surveillance as SV
from .db import get_db
from .models import Country, Disease, Indicator, Observation, OutbreakAlert, Source
from .routes import country_name
from .routes_extra import source_health
from .routes_surv import _board_rows

router = APIRouter(prefix="/api/pulse")

_CACHE: dict = {}
_LOCK = threading.Lock()


def _cached(key, ttl, fn):
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    val = fn()
    with _LOCK:
        _CACHE[key] = (now, val)
        if len(_CACHE) > 48:
            _CACHE.pop(next(iter(_CACHE)))
    return val


def _stamp(db: Session):
    return (db.scalar(select(func.count()).select_from(Observation)),
            db.scalar(select(func.max(Observation.id))),
            db.scalar(select(func.count()).select_from(OutbreakAlert)))


def _age(kind: str, amount: float) -> str:
    """fresh / aging / old, with thresholds that fit the clock of each layer."""
    lim = {"weekly": (14, 45), "alert": (7, 30), "annual": (2, 4)}[kind]
    return "fresh" if amount <= lim[0] else "aging" if amount <= lim[1] else "old"


def _name(o, lang: str) -> str:
    return (o.name_fa if lang == "fa" and o.name_fa else o.name_en)


def _build(db: Session, lang: str) -> dict:
    today = SV.today()
    year_now = today.year

    # ---- weekly surveillance (reuses the early-warning board)
    weekly = []
    for r in _board_rows(lang, db):
        end = date.fromisoformat(r["as_of"])
        age_days = (today - end).days
        weekly.append({**r, "age_days": age_days, "freshness": _age("weekly", age_days)})

    # ---- latest outbreak alerts
    cs = {c.iso3: c for c in db.scalars(select(Country))}
    ds = {d.id: d for d in db.scalars(select(Disease))}
    alerts = []
    for a in db.scalars(select(OutbreakAlert).order_by(OutbreakAlert.published_at.desc()).limit(12)):
        age_days = (datetime.utcnow() - a.published_at).days if a.published_at else None
        alerts.append(dict(
            title=a.title, url=a.url, source=a.source, published_at=a.published_at.isoformat() if a.published_at else None,
            country=country_name(cs[a.country_iso3], lang) if a.country_iso3 in cs else None, country_iso3=a.country_iso3,
            disease=_name(ds[a.disease_id], lang) if a.disease_id in ds else None,
            age_days=age_days, freshness=_age("alert", age_days) if age_days is not None else "old"))

    # ---- annual burden: latest year per indicator, both sexes, all ages
    sel = (Observation.sex == "ALL", Observation.age_group == "ALL")
    latest = (select(Observation.indicator_id.label("iid"), func.max(Observation.year).label("yr"))
              .where(*sel).group_by(Observation.indicator_id).subquery())
    rows = db.execute(
        select(Observation.indicator_id, Observation.year, Observation.country_iso3, Observation.value)
        .join(latest, (Observation.indicator_id == latest.c.iid) & (Observation.year == latest.c.yr))
        .where(*sel)).all()
    by_ind: dict[int, dict] = {}
    for iid, yr, iso, v in rows:
        e = by_ind.setdefault(iid, dict(year=yr, vals=[]))
        e["vals"].append((iso, v))
    inds = {i.id: i for i in db.scalars(select(Indicator))}
    srcs = {s.id: s for s in db.scalars(select(Source))}
    burden = []
    for iid, e in by_ind.items():
        ind = inds.get(iid)
        if ind is None:
            continue
        vals = e["vals"]
        worst = max(vals, key=lambda t: t[1]) if ind.higher_is_worse else min(vals, key=lambda t: t[1])
        dz = ds.get(ind.disease_id)
        age = year_now - e["year"]
        burden.append(dict(
            code=ind.code, name=_name(ind, lang), unit=ind.unit, measure=ind.measure,
            higher_is_worse=ind.higher_is_worse, age_standardized=ind.age_standardized,
            disease=_name(dz, lang) if dz else None, disease_slug=dz.slug if dz else None,
            category=dz.category if dz else None, year=e["year"], n=len(vals),
            median=statistics.median(v for _, v in vals),
            total=sum(v for _, v in vals) if ind.unit == "count" else None,
            extreme=dict(iso3=worst[0], name=country_name(cs[worst[0]], lang) if worst[0] in cs else worst[0], value=worst[1]),
            source=dict(code=srcs[ind.source_id].code, name=srcs[ind.source_id].name,
                        synthetic=srcs[ind.source_id].is_synthetic) if ind.source_id in srcs else None,
            age_years=age, freshness=_age("annual", age)))
    burden.sort(key=lambda r: ((r["disease"] or "~"), r["measure"], r["name"]))

    return dict(
        generated_at=datetime.utcnow().isoformat(timespec="seconds"), today=today.isoformat(),
        weekly=weekly, alerts=alerts, burden=burden,
        sources=source_health(db)["jobs"],
        thresholds=dict(weekly_days=[14, 45], alert_days=[7, 30], annual_years=[2, 4]),
        n_countries=len(cs),
    )


@router.get("")
def pulse(lang: str = "en", db: Session = Depends(get_db)):
    return _cached(("pulse", lang, SV.today(), _stamp(db)), 300, lambda: _build(db, lang))


@router.get("/country/{iso3}")
def country_pulse(iso3: str, lang: str = "en", db: Session = Depends(get_db)):
    """Latest value of every indicator for one country, with rank among countries measured in the same year."""
    iso = iso3.upper()
    c = db.get(Country, iso)
    if c is None:
        raise HTTPException(404, "Unknown country")
    sel = (Observation.sex == "ALL", Observation.age_group == "ALL")
    own = db.execute(select(Observation).where(Observation.country_iso3 == iso, *sel)
                     .order_by(Observation.indicator_id, Observation.year.desc())).scalars().all()
    first: dict[int, Observation] = {}
    for o in own:
        first.setdefault(o.indicator_id, o)
    if not first:
        return dict(country=dict(iso3=iso, name=country_name(c, lang)), items=[], alerts=[])
    pairs = [(o.indicator_id, o.year) for o in first.values()]
    slices: dict[tuple[int, int], list[float]] = {}
    for iid, yr, v in db.execute(select(Observation.indicator_id, Observation.year, Observation.value)
                                 .where(tuple_(Observation.indicator_id, Observation.year).in_(pairs), *sel)):
        slices.setdefault((iid, yr), []).append(v)
    inds = {i.id: i for i in db.scalars(select(Indicator).where(Indicator.id.in_(list(first))))}
    ds = {d.id: d for d in db.scalars(select(Disease))}
    year_now = SV.today().year
    items = []
    for iid, o in first.items():
        ind = inds[iid]
        vs = slices.get((iid, o.year), [o.value])
        worse = sum(1 for v in vs if (v > o.value if ind.higher_is_worse else v < o.value))  # countries doing worse
        dz = ds.get(ind.disease_id)
        items.append(dict(
            code=ind.code, name=_name(ind, lang), unit=ind.unit, measure=ind.measure,
            disease=_name(dz, lang) if dz else None, disease_slug=dz.slug if dz else None,
            year=o.year, value=o.value, low=o.low, high=o.high, quality=o.data_quality,
            rank_worst=worse + 1, of=len(vs), median=statistics.median(vs),
            age_years=year_now - o.year, freshness=_age("annual", year_now - o.year),
            higher_is_worse=ind.higher_is_worse))
    items.sort(key=lambda r: ((r["disease"] or "~"), r["measure"], r["name"]))
    al = [dict(title=a.title, url=a.url, published_at=a.published_at.isoformat() if a.published_at else None)
          for a in db.scalars(select(OutbreakAlert).where(OutbreakAlert.country_iso3 == iso)
                              .order_by(OutbreakAlert.published_at.desc()).limit(5))]
    return dict(country=dict(iso3=iso, name=country_name(c, lang), population=c.population), items=items, alerts=al)
