"""Data for the animated bubble chart and the country-similarity network.

Both only reshape rows that are already in the database (sex=ALL, age=ALL, same selection as the map).
Nothing is imputed: a country appears in a frame only if it has a real value for every indicator the frame uses.
"""
from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Country, Indicator, Observation
from .queries import indicator_dict
from .routes import country_name

router = APIRouter(prefix="/api/viz")

MIN_COUNTRIES = 15          # a chart frame with fewer countries than this is not worth animating
PREFERRED = [("MDG_0000000026", "WHOSIS_000003"), ("WHS4_100", "WHOSIS_000003")]  # sensible default pairs

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
        if len(_CACHE) > 64:
            _CACHE.pop(next(iter(_CACHE)))
    return val


def _stamp(db: Session):
    return (db.scalar(select(func.count()).select_from(Observation)),
            db.scalar(select(func.max(Observation.id))))


def _ind(db: Session, code: str) -> Indicator:
    ind = db.scalar(select(Indicator).where(Indicator.code == code))
    if ind is None:
        raise HTTPException(404, f"Unknown indicator: {code}")
    return ind


def _values(db: Session, ind_id: int) -> dict[tuple[str, int], float]:
    rows = db.execute(select(Observation.country_iso3, Observation.year, Observation.value).where(
        Observation.indicator_id == ind_id, Observation.sex == "ALL", Observation.age_group == "ALL"))
    return {(i, y): v for i, y, v in rows}


@router.get("/options")
def options(lang: str = "en", db: Session = Depends(get_db)):
    """Indicators that have enough countries and years to be drawn, plus a default pair."""
    rows = db.execute(
        select(Observation.indicator_id, func.count(func.distinct(Observation.country_iso3)),
               func.count(func.distinct(Observation.year)))
        .where(Observation.sex == "ALL", Observation.age_group == "ALL")
        .group_by(Observation.indicator_id)).all()
    ok = {i: (c, y) for i, c, y in rows if c >= MIN_COUNTRIES and y >= 2}
    inds = [i for i in db.scalars(select(Indicator)) if i.id in ok]
    out = [dict(code=i.code, name=(i.name_fa if lang == "fa" and i.name_fa else i.name_en), unit=i.unit,
                higher_is_worse=i.higher_is_worse, countries=ok[i.id][0], years=ok[i.id][1]) for i in inds]
    out.sort(key=lambda r: r["name"])
    codes = {r["code"] for r in out}
    default = next(({"x": a, "y": b} for a, b in PREFERRED if a in codes and b in codes), None)
    if default is None and len(out) >= 2:
        best = sorted(out, key=lambda r: -r["countries"] * r["years"])[:2]
        default = {"x": best[0]["code"], "y": best[1]["code"]}
    return dict(indicators=out, default=default)


@router.get("/bubbles")
def bubbles(x: str, y: str, lang: str = "en", db: Session = Depends(get_db)):
    if x == y:
        raise HTTPException(422, "Choose two different indicators")
    ix, iy = _ind(db, x), _ind(db, y)
    vx, vy = _values(db, ix.id), _values(db, iy.id)
    both = sorted(set(vx) & set(vy))                      # (iso3, year) pairs where both are measured
    by_year: dict[int, int] = {}
    for _, yr in both:
        by_year[yr] = by_year.get(yr, 0) + 1
    years = sorted(yr for yr, n in by_year.items() if n >= MIN_COUNTRIES)
    if len(years) < 2:
        raise HTTPException(404, "These two indicators share too few countries and years to animate")
    keep = set(years)
    series: dict[str, list] = {}
    for iso, yr in both:
        if yr in keep:
            series.setdefault(iso, []).append([yr, round(vx[(iso, yr)], 4), round(vy[(iso, yr)], 4)])
    cs = {c.iso3: c for c in db.scalars(select(Country).where(Country.iso3.in_(list(series))))}
    countries = [dict(iso3=i, name=country_name(cs[i], lang), region=cs[i].who_region or cs[i].region,
                      population=cs[i].population, income=cs[i].income_group, points=series[i])
                 for i in sorted(series) if i in cs]
    xs = [p[1] for c in countries for p in c["points"]]
    ys = [p[2] for c in countries for p in c["points"]]
    return dict(x=indicator_dict(ix, lang), y=indicator_dict(iy, lang), years=years, countries=countries,
                x_range=[min(xs), max(xs)], y_range=[min(ys), max(ys)],
                per_year=[by_year[yr] for yr in years],
                population_year=db.scalar(select(func.max(Country.population_year))))


# ---------------------------------------------------------------- similarity network

def _percentile_ranks(vals: dict[str, float]) -> dict[str, float]:
    order = sorted(vals, key=lambda k: vals[k])
    n = len(order)
    out: dict[str, float] = {}
    i = 0
    while i < n:                                          # ties share the average rank
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        r = (i + j) / 2 / max(n - 1, 1)
        for k in order[i:j + 1]:
            out[k] = r
        i = j + 1
    return out


def _label_propagation(nodes: list[str], adj: dict[str, dict[str, float]]) -> dict[str, str]:
    """Deterministic weighted label propagation (fixed visiting order, ties -> smallest label)."""
    label = {n: n for n in nodes}
    for _ in range(25):
        changed = False
        for n in nodes:
            score: dict[str, float] = {}
            for m, w in adj[n].items():
                score[label[m]] = score.get(label[m], 0.0) + w
            if not score:
                continue
            top = max(score.values())
            best = min(k for k, v in score.items() if v == top)
            if best != label[n]:
                label[n] = best
                changed = True
        if not changed:
            break
    return label


def _build_similarity(db: Session, lang: str, k: int, min_shared: int) -> dict:
    inds = list(db.scalars(select(Indicator)))
    latest: dict[str, dict[str, float]] = {}              # indicator code -> {iso3: latest value}
    used: list[Indicator] = []
    for ind in inds:
        rows = db.execute(select(Observation.country_iso3, Observation.year, Observation.value).where(
            Observation.indicator_id == ind.id, Observation.sex == "ALL", Observation.age_group == "ALL")).all()
        best: dict[str, tuple[int, float]] = {}
        for iso, yr, v in rows:
            if iso not in best or yr > best[iso][0]:
                best[iso] = (yr, v)
        if len(best) >= 60:                               # too sparse indicators would add noise, not signal
            latest[ind.code] = {i: v for i, (_, v) in best.items()}
            used.append(ind)
    if len(used) < min_shared:
        raise HTTPException(404, f"Need at least {min_shared} indicators with 60+ countries; have {len(used)}")
    rank = {code: _percentile_ranks(v) for code, v in latest.items()}
    vec: dict[str, dict[str, float]] = {}
    for code, rk in rank.items():
        for iso, r in rk.items():
            vec.setdefault(iso, {})[code] = r
    nodes = sorted(i for i, v in vec.items() if len(v) >= min_shared)
    if len(nodes) < 10:
        raise HTTPException(404, "Too few countries have enough indicators")

    def dist(a: str, b: str) -> float | None:
        sh = vec[a].keys() & vec[b].keys()
        if len(sh) < min_shared:
            return None
        return sum(abs(vec[a][c] - vec[b][c]) for c in sh) / len(sh)

    nbr: dict[str, list[tuple[float, str]]] = {n: [] for n in nodes}
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            d = dist(a, b)
            if d is not None:
                nbr[a].append((d, b))
                nbr[b].append((d, a))
    edges: dict[tuple[str, str], float] = {}
    for a in nodes:
        for d, b in sorted(nbr[a])[:k]:
            edges[tuple(sorted((a, b)))] = round(1 - d, 4)
    adj: dict[str, dict[str, float]] = {n: {} for n in nodes}
    for (a, b), w in edges.items():
        adj[a][b] = w
        adj[b][a] = w
    label = _label_propagation(nodes, adj)
    sizes: dict[str, int] = {}
    for n in nodes:
        sizes[label[n]] = sizes.get(label[n], 0) + 1
    order = sorted(sizes, key=lambda c: (-sizes[c], c))
    cid = {c: i for i, c in enumerate(order)}

    cs = {c.iso3: c for c in db.scalars(select(Country))}
    by_code = {i.code: i for i in used}
    clusters = []
    for lab in order:
        members = [n for n in nodes if label[n] == lab]
        feats = []
        for code in rank:
            ms = [rank[code][m] for m in members if m in rank[code]]
            rest = [r for n, r in rank[code].items() if n in label and label[n] != lab]
            if len(ms) >= max(3, len(members) // 2) and rest:
                delta = sum(ms) / len(ms) - sum(rest) / len(rest)
                feats.append((abs(delta), delta, code))
        feats.sort(reverse=True)
        top = [dict(code=c, name=(by_code[c].name_fa if lang == "fa" and by_code[c].name_fa else by_code[c].name_en),
                    direction="high" if d > 0 else "low", delta=round(d, 3)) for _, d, c in feats[:3]]
        pops = sorted(members, key=lambda m: -(cs[m].population or 0))[:3]
        clusters.append(dict(id=cid[lab], size=len(members), features=top,
                             examples=[country_name(cs[m], lang) for m in pops]))
    return dict(
        nodes=[dict(iso3=n, name=country_name(cs[n], lang), region=cs[n].who_region or cs[n].region,
                    cluster=cid[label[n]], n_indicators=len(vec[n]), population=cs[n].population) for n in nodes],
        edges=[dict(s=a, t=b, w=w) for (a, b), w in sorted(edges.items())],
        clusters=clusters,
        indicators=[dict(code=i.code, name=(i.name_fa if lang == "fa" and i.name_fa else i.name_en)) for i in used],
        k=k, min_shared=min_shared,
        method=("Each country is a vector of percentile ranks (latest year, both sexes) over the indicators; distance is "
                "the mean absolute rank difference over shared indicators; each country links to its k nearest "
                "countries; groups come from weighted label propagation. This shows statistical similarity of "
                "reported burden, not disease transmission."),
    )


@router.get("/similarity")
def similarity(lang: str = "en", k: int = Query(4, ge=2, le=8), min_shared: int = Query(4, ge=3, le=12),
               db: Session = Depends(get_db)):
    key = ("sim", lang, k, min_shared, _stamp(db))
    return _cached(key, 600, lambda: _build_similarity(db, lang, k, min_shared))
