"""Refresh all live feeds in one go. Designed for a scheduler (GitHub Actions cron, cron, n8n).

Each job is isolated: one failing feed never blocks the others, and every outcome (including network
errors that happen before a loader starts) is written to `etl_run`, so /api/health/sources and the site
show exactly which feed is stale. Exit code is 0 only if every enabled job succeeded.

Feeds are listed in etl/live_feeds.json. CDC NNDSS entries need a `label` and `geo` taken from
`python -m etl.run surv cdc-inspect`, so they ship disabled.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy.orm import Session

from etl.common import Run

FEEDS = Path(__file__).with_name("live_feeds.json")


def _dispatch(db: Session, feed: dict) -> dict:
    from etl import surveillance as S

    k = feed["kind"]
    if k == "who-gho":
        from etl.who_gho import load_who
        return load_who(db, feed.get("only"))
    if k == "who-don":
        from etl.alerts import load_alerts
        return load_alerts(db)
    if k == "owid-mpox":
        return S.load_owid_mpox(db, feed.get("source") or S.OWID_MPOX_URL)
    if k == "who-covid":
        return S.load_who_covid(db, feed.get("source") or S.WHO_COVID_URL)
    if k == "delphi-fluview":
        return S.load_delphi_fluview(db)
    if k == "cdc-nndss":
        return S.load_cdc_nndss(db, feed["disease"], feed["label"], feed["geo"], feed.get("dataset", "x9gk-5huc"))
    if k == "csv":
        return S.load_csv_weekly(db, feed["source"], feed["disease"], date_col=feed["date_col"],
                                 value_col=feed["value_col"], country_col=feed["country_col"],
                                 country_kind=feed.get("country_kind", "iso3"),
                                 cumulative=feed.get("cumulative", False), date_format=feed.get("date_format"))
    raise ValueError(f"unknown feed kind {k!r}")


def run_live(db: Session, only: list[str] | None = None, feeds_path: Path = FEEDS, retries: int = 2) -> dict:
    feeds = json.loads(feeds_path.read_text())
    report = {}
    for feed in feeds:
        name = feed["name"]
        if only and name not in only:
            continue
        if not feed.get("enabled", True):
            report[name] = {"status": "disabled", "hint": feed.get("hint", "")}
            continue
        last_err = None
        for attempt in range(retries + 1):
            try:
                report[name] = {"status": "ok", "result": _dispatch(db, feed)}
                break
            except Exception as e:  # noqa: BLE001 - isolate every feed
                db.rollback()
                last_err = f"{type(e).__name__}: {e}"
                time.sleep(2 * (attempt + 1) if attempt < retries else 0)
        else:
            try:
                with Run(db, f"live:{name}"):  # records the failure for /api/health/sources
                    raise RuntimeError(last_err)
            except RuntimeError:
                pass
            report[name] = {"status": "failed", "error": last_err}
    return report
