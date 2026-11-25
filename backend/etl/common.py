from __future__ import annotations

import time
from datetime import datetime
from typing import Iterable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EtlRun, Indicator, Observation, Source

USER_AGENT = "global-health-atlas/0.1 (open humanitarian project)"


def http_get_json(url: str, params: dict | None = None, retries: int = 3, timeout: float = 90.0):
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = httpx.get(
                url,
                params=params,
                timeout=timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 - network layer, retry any
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last}")


def get_or_create_source(db: Session, code: str, **fields) -> Source:
    src = db.scalar(select(Source).where(Source.code == code))
    if src is None:
        src = Source(code=code, **fields)
        db.add(src)
        db.flush()
    else:
        for k, v in fields.items():
            setattr(src, k, v)
    return src


def upsert_indicator(db: Session, code: str, **fields) -> Indicator:
    ind = db.scalar(select(Indicator).where(Indicator.code == code))
    if ind is None:
        ind = Indicator(code=code, **fields)
        db.add(ind)
        db.flush()
    else:
        for k, v in fields.items():
            setattr(ind, k, v)
    return ind


def upsert_observations(db: Session, indicator_id: int, rows: Iterable[dict]) -> int:
    """rows: dicts with country_iso3, year, sex, age_group, value, low, high, data_quality.

    Idempotent: existing (country, year, sex, age_group) rows are updated in place.
    """
    existing = {
        (o.country_iso3, o.year, o.sex, o.age_group): o
        for o in db.scalars(select(Observation).where(Observation.indicator_id == indicator_id))
    }
    now = datetime.utcnow()
    new_rows, n = [], 0
    for r in rows:
        key = (r["country_iso3"], r["year"], r.get("sex", "ALL"), r.get("age_group", "ALL"))
        o = existing.get(key)
        if o is not None:
            o.value, o.low, o.high = r["value"], r.get("low"), r.get("high")
            o.data_quality, o.retrieved_at = r.get("data_quality", "estimated"), now
        else:
            new_rows.append(
                dict(
                    indicator_id=indicator_id,
                    country_iso3=key[0],
                    year=key[1],
                    sex=key[2],
                    age_group=key[3],
                    value=r["value"],
                    low=r.get("low"),
                    high=r.get("high"),
                    data_quality=r.get("data_quality", "estimated"),
                    retrieved_at=now,
                )
            )
            existing[key] = True  # type: ignore[assignment]  # guard against dup keys in input
        n += 1
    if new_rows:
        db.bulk_insert_mappings(Observation, new_rows)
    db.flush()
    return n


class Run:
    """Context manager that records an ETL run in the etl_run table."""

    def __init__(self, db: Session, job: str):
        self.db, self.job = db, job
        self.rec = EtlRun(job=job)
        self.rows = 0

    def __enter__(self):
        self.db.add(self.rec)
        self.db.flush()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.rec.finished_at = datetime.utcnow()
        self.rec.rows_written = self.rows
        self.rec.status = "failed" if exc_type else "ok"
        if exc:
            self.rec.message = str(exc)[:2000]
            self.db.rollback()
            self.db.add(self.rec)
        self.db.commit()
        return False
