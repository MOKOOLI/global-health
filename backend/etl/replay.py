"""Replay a disease's history through the early-warning engine and report WHEN it would have warned.

Every week is assessed using only data available at that week (the engine is causal), so this is an
honest back-test of the detector, not a fit to hindsight. Compare the dates with real-world milestones
(WHO declarations, DONs) to judge lead/lag. Run:  python -m etl.run replay covid-19
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import surveillance as SV
from app.models import Disease

SEVERITY = ["none", "watch", "single_country", "regional_outbreak", "novel_spread",
            "multi_region_outbreak", "pandemic_pattern"]


def replay_report(db: Session, slug: str) -> dict:
    disease = db.scalar(select(Disease).where(Disease.slug == slug))
    loaded = SV.load_disease(db, disease) if disease else None
    if loaded is None:
        raise ValueError(f"no surveillance series for {slug!r}")
    tl = SV.replay(loaded)
    first: dict[str, dict] = {}
    for r in tl:
        for lvl in SEVERITY[1:]:
            if r["level"] == lvl and lvl not in first:
                first[lvl] = {k: r[k] for k in ("week_start", "n_epidemic", "n_watch", "n_regions", "n_reporting")}
    share = Counter(r["level"] for r in tl)
    total = len(tl)
    transitions, prev = 0, None
    for r in tl:
        transitions += r["level"] != prev
        prev = r["level"]
    smoothed = sorted(iso for iso, sd in loaded.series.items() if sd.smoothed)
    return dict(
        disease=slug, countries=len(loaded.series), weeks=total, first_week=tl[0]["week_start"],
        last_week=tl[-1]["week_start"],
        first_reached={lvl: first[lvl] for lvl in SEVERITY if lvl in first},
        share_of_weeks={lvl: round(share[lvl] / total, 3) for lvl in SEVERITY if share[lvl]},
        level_changes=transitions, batch_reporting_countries=len(smoothed),
        timeline=tl,
    )
