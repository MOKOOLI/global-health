from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import llm
from . import surveillance as SV
from .db import get_db
from .models import Country, Disease

router = APIRouter(prefix="/api/surveillance")


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(422, "as_of must be YYYY-MM-DD") from None


def _loaded(db: Session, slug: str) -> SV.Loaded:
    d = db.scalar(select(Disease).where(Disease.slug == slug))
    loaded = SV.load_disease(db, d) if d else None
    if loaded is None:
        raise HTTPException(404, f"No surveillance data for {slug!r}")
    return loaded


def _pattern_out(p: dict) -> dict:
    return {**p, "label": SV.PATTERNS[p["level"]]}


@router.get("/meta")
def meta():
    return dict(phases=SV.PHASES, patterns=SV.PATTERNS, pattern_note=SV.PATTERN_NOTE,
                pattern_rules=SV.PATTERN_RULES)


@router.get("/diseases")
def diseases(lang: str = "en", db: Session = Depends(get_db)):
    out = []
    for d in SV.diseases_with_series(db):
        L = SV.load_disease(db, d)
        if L is None:
            continue
        end = SV.dataset_as_of(L)
        out.append(dict(
            slug=d.slug, name=d.name_fa if lang == "fa" else d.name_en, n_countries=len(L.series),
            start=L.ds_start.isoformat() if L.ds_start else None, end=end.isoformat(),
            weeks_behind_today=SV.weeks_behind_today(end),
            sources=sorted({sd.source_code for sd in L.series.values()}),
        ))
    return out


_BOARD: dict[tuple, tuple[float, list]] = {}
import threading  # noqa: E402

_BOARD_LOCK = threading.Lock()
_BOARD_TTL = 300.0   # seconds; the underlying data change at most weekly


def _data_sig(db: Session) -> tuple:
    from sqlalchemy import func
    from .models import SurveillanceWeekly  # noqa: PLC0415
    return tuple(db.execute(select(func.count(), func.max(SurveillanceWeekly.week_start))).one())


@router.get("/board")
def board(lang: str = "en", db: Session = Depends(get_db)):
    """One row per disease: current multi-country pattern and the most urgent countries (cached 5 min per data signature)."""
    import time
    key = (lang, _data_sig(db))
    hit = _BOARD.get(key)
    if hit and time.time() - hit[0] < _BOARD_TTL:
        return hit[1]
    with _BOARD_LOCK:                      # one computation at a time: concurrent first hits must not all recompute
        hit = _BOARD.get(key)
        if hit and time.time() - hit[0] < _BOARD_TTL:
            return hit[1]
        rows = _board_rows(lang, db)
        if len(_BOARD) > 8:
            _BOARD.clear()
        _BOARD[key] = (time.time(), rows)
    return rows


def _board_rows(lang: str, db: Session) -> list:
    rows = []
    for d in SV.diseases_with_series(db):
        L = SV.load_disease(db, d)
        if L is None:
            continue
        end = SV.dataset_as_of(L)
        st = SV.statuses(L, end, lang)
        p = SV.pattern(st)
        top = sorted([r for r in st if not r["stale"] and r["score"] > 0], key=lambda r: -r["score"])[:5]
        rows.append(dict(
            slug=d.slug, name=d.name_fa if lang == "fa" else d.name_en, as_of=end.isoformat(),
            weeks_behind_today=SV.weeks_behind_today(end), pattern=_pattern_out(p),
            top=[dict(iso3=r["iso3"], name=r["name"], phase=r["phase"], trend=r["trend"], ratio=r["ratio"])
                 for r in top],
        ))
    order = {k: i for i, k in enumerate(["pandemic_pattern", "novel_spread", "multi_region_outbreak",
                                         "regional_outbreak", "single_country", "watch", "none"])}
    rows.sort(key=lambda r: order.get(r["pattern"]["level"], 9))
    return rows


@router.get("/{slug}/status")
def status(slug: str, as_of: str | None = None, lang: str = "en", db: Session = Depends(get_db)):
    """All countries' phase at `as_of` (default: newest data), plus the multi-country pattern."""
    L = _loaded(db, slug)
    end = SV.dataset_as_of(L)
    when = min(_parse_date(as_of) or end, end)
    st = SV.statuses(L, when, lang)
    num = {c.iso3: c.iso_numeric for c in db.scalars(select(Country))}
    for r in st:
        r["iso_numeric"] = num.get(r["iso3"])
    st.sort(key=lambda r: (-r["score"], r["name"]))
    return dict(
        disease=slug, as_of=when.isoformat(), dataset_start=L.ds_start.isoformat() if L.ds_start else None,
        dataset_end=end.isoformat(), weeks_behind_today=SV.weeks_behind_today(end),
        pattern=_pattern_out(SV.pattern(st)), rows=st,
        generation_interval=dict(mean=L.gi[0], sd=L.gi[1]) if L.gi else None,
    )


@router.get("/{slug}/series/{iso3}")
async def series(slug: str, iso3: str, as_of: str | None = None, forecast: bool = True, lang: str = "en",
                 narrate: bool = False, db: Session = Depends(get_db)):
    L = _loaded(db, slug)
    out = SV.series_detail(L, iso3.upper(), _parse_date(as_of), forecast, lang)
    if out is None:
        raise HTTPException(404, "No series for this country/date")
    out["smoothed"] = L.series[iso3.upper()].smoothed
    if narrate:
        out["narrative"] = await llm.narrate(out["findings"], lang)
    return out


@router.get("/{slug}/replay")
def replay(slug: str, db: Session = Depends(get_db)):
    """Back-test timeline: the pattern level each week using only the data known at that week."""
    L = _loaded(db, slug)
    return dict(disease=slug, timeline=SV.replay(L))


_FRAMES: dict[tuple, dict] = {}


@router.get("/{slug}/frames")
def frames(slug: str, step: int = 2, lang: str = "en", db: Session = Depends(get_db)):
    """Whole-history replay as compact frames for the animated map (cached per data signature)."""
    L = _loaded(db, slug)
    step = min(max(step, 1), 8)
    sig = (slug, step, len(L.series), SV.dataset_as_of(L))
    if sig not in _FRAMES:
        if len(_FRAMES) > 16:
            _FRAMES.clear()
        _FRAMES[sig] = SV.frames(L, step)
    f = _FRAMES[sig]
    meta = {c.iso3: c for c in db.scalars(select(Country).where(Country.iso3.in_(f["countries"])))}
    return dict(f, disease=slug,
                numeric=[meta[i].iso_numeric if i in meta else None for i in f["countries"]],
                names=[(meta[i].name_fa if lang == "fa" and meta[i].name_fa else meta[i].name_en) if i in meta else i
                       for i in f["countries"]])
