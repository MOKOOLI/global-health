"""CSV export, citation text and data-freshness for the education / trust features."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import dataset
from . import surveillance as SV
from .config import settings
from .db import get_db
from .models import Country, Disease, EtlRun, Indicator, Observation, Source

router = APIRouter(prefix="/api")


def _csv(rows: list[list], header: list[str], filename: str) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    # UTF-8 BOM so Excel opens Persian/accented names correctly
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/export/indicator/{code}.csv")
def export_indicator(code: str, sex: str | None = None, age: str | None = None, db: Session = Depends(get_db)):
    ind = db.scalar(select(Indicator).where(Indicator.code == code))
    if ind is None:
        raise HTTPException(404, "Unknown indicator")
    src = ind.source
    ver = dataset.indicator_version(db, ind)
    rows = [r + [ind.code, ind.unit, src.name, src.license or "", ver, "synthetic-demo-data" if src.is_synthetic else ""]
            for r in dataset.indicator_csv_rows(db, ind, sex, age)]
    head = dataset.CSV_HEADER + ["indicator", "unit", "source", "source_license", "data_version", "flag"]
    resp = _csv(rows, head, f"{ind.code}.csv")
    resp.headers["X-Data-Version"] = ver
    return resp


@router.get("/datapackage/{code}.json")
def datapackage(code: str, db: Session = Depends(get_db)):
    ind = db.scalar(select(Indicator).where(Indicator.code == code))
    if ind is None:
        raise HTTPException(404, "Unknown indicator")
    return dataset.datapackage(db, ind, path=f"/api/export/indicator/{code}.csv")


@router.get("/export/surveillance/{slug}/{iso3}.csv")
def export_series(slug: str, iso3: str, db: Session = Depends(get_db)):
    d = db.scalar(select(Disease).where(Disease.slug == slug))
    L = SV.load_disease(db, d) if d else None
    sd = L.series.get(iso3.upper()) if L else None
    if sd is None:
        raise HTTPException(404, "No weekly series")
    rows = []
    for i, day in enumerate(sd.dates):
        rows.append([iso3.upper(), day.isoformat(), float(sd.raw[i]) if sd.raw is not None and sd.raw[i] == sd.raw[i] else "",
                     round(float(sd.base.expected[i]), 3), round(float(sd.base.upper[i]), 3), sd.source_code])
    return _csv(rows, ["iso3", "week_start", "reported", "expected_baseline", "upper_limit", "source"],
                f"{slug}-{iso3.upper()}-weekly.csv")


def _base() -> str:
    return settings.public_url.rstrip("/")


@router.get("/cite")
def cite(kind: str, key: str, lang: str = "en", db: Session = Depends(get_db)):
    """APA + BibTeX text. `kind` = indicator | surveillance; `key` = indicator code | disease slug."""
    today = date.today()
    if kind == "indicator":
        ind = db.scalar(select(Indicator).where(Indicator.code == key))
        if ind is None:
            raise HTTPException(404, "Unknown indicator")
        src = db.get(Source, ind.source_id)
        title, url = f"{ind.name_en} (data via Global Health Atlas)", f"{_base()}/en/disease/{key}"
        origin = f"{src.name}. {src.citation or ''}".strip()
        version = dataset.indicator_version(db, ind)
    elif kind == "surveillance":
        d = db.scalar(select(Disease).where(Disease.slug == key))
        if d is None:
            raise HTTPException(404, "Unknown disease")
        title, url = f"Early-warning signals for {d.name_en}", f"{_base()}/en/surveillance"
        origin = "Underlying weekly counts: see sources listed on the Data & API page."
        version = None
    else:
        raise HTTPException(422, "kind must be indicator or surveillance")
    year = today.year
    vtxt = f" Data version {version}." if version else ""
    apa = (f"Global Health Atlas. ({year}). {title}.{vtxt} Retrieved {today.strftime('%B %d, %Y')}, from {url}. "
           f"Original data: {origin}")
    bib_key = "gha" + str(year) + "".join(ch for ch in key if ch.isalnum())[:20]
    bib = (f"@misc{{{bib_key},\n  title        = {{{title}}},\n  author       = {{{{Global Health Atlas}}}},\n"
           f"  year         = {{{year}}},\n  version      = {{{version or ''}}},\n  url          = {{{url}}},\n  note         = {{Accessed {today.isoformat()}. "
           f"Original data: {origin}}}\n}}")
    return dict(apa=apa, bibtex=bib, url=url,
                notice="Cite the original data provider as well. This text is generated; check it against your journal's style.")


@router.get("/health/sources")
def source_health(db: Session = Depends(get_db)):
    """Freshness per ETL job: last success, last failure, rows. Lets users (and monitors) see stale feeds."""
    jobs = db.execute(select(EtlRun.job, func.max(EtlRun.started_at)).group_by(EtlRun.job)).all()
    out = []
    for job, _ in jobs:
        ok = db.scalar(select(EtlRun).where(EtlRun.job == job, EtlRun.status == "ok").order_by(EtlRun.id.desc()))
        bad = db.scalar(select(EtlRun).where(EtlRun.job == job, EtlRun.status == "failed").order_by(EtlRun.id.desc()))
        last = db.scalar(select(EtlRun).where(EtlRun.job == job).order_by(EtlRun.id.desc()))
        out.append(dict(
            job=job, last_status=last.status,
            last_ok=ok.finished_at.isoformat() if ok and ok.finished_at else None,
            last_ok_rows=ok.rows_written if ok else None,
            last_failure=bad.finished_at.isoformat() if bad and bad.finished_at else None,
            last_failure_message=(bad.message or "")[:300] if bad and (not ok or bad.id > ok.id) else None,
            age_hours=round((datetime.utcnow() - ok.finished_at).total_seconds() / 3600, 1) if ok and ok.finished_at else None,
        ))
    return dict(jobs=sorted(out, key=lambda r: r["job"]), time=datetime.utcnow().isoformat())


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness probe: the database answers."""
    from sqlalchemy import text

    try:
        db.execute(text("select 1"))
    except Exception:  # noqa: BLE001
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ready"}
