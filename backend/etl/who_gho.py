"""WHO Global Health Observatory (GHO) OData API loader.

API docs: https://www.who.int/data/gho/info/gho-odata-api
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Disease
from etl.common import (
    Run,
    get_or_create_source,
    http_get_json,
    upsert_indicator,
    upsert_observations,
)
from etl.indicators_config import WHO_INDICATORS

BASE = "https://ghoapi.azureedge.net/api"
SEX_MAP = {"SEX_BTSX": "ALL", "SEX_MLE": "M", "SEX_FMLE": "F"}


def discover(keyword: str) -> list[tuple[str, str]]:
    """List GHO indicators whose name contains `keyword` (use to find/verify codes)."""
    kw = keyword.replace("'", "''")
    data = http_get_json(f"{BASE}/Indicator", {"$filter": f"contains(IndicatorName,'{kw}')"})
    return [(i["IndicatorCode"], i["IndicatorName"]) for i in data.get("value", [])]


def official_name(code: str) -> str | None:
    data = http_get_json(f"{BASE}/Indicator", {"$filter": f"IndicatorCode eq '{code}'"})
    vals = data.get("value", [])
    return vals[0]["IndicatorName"] if vals else None


def fetch_rows(code: str) -> list[dict]:
    """All country-level rows for an indicator, following OData paging."""
    url, params, out = f"{BASE}/{code}", {"$filter": "SpatialDimType eq 'COUNTRY'"}, []
    while url:
        data = http_get_json(url, params)
        out.extend(data.get("value", []))
        url, params = data.get("@odata.nextLink"), None
    return out


def parse_rows(raw: list[dict], quality: str) -> list[dict]:
    rows = []
    for r in raw:
        if r.get("TimeDimType") != "YEAR" or r.get("NumericValue") is None:
            continue
        # We only keep total / by-sex breakdowns here. Rows with other dimensions
        # (age group, residence, wealth quintile...) are skipped to avoid mixing strata.
        dim1 = r.get("Dim1")
        if dim1 is not None and dim1 not in SEX_MAP:
            continue
        if r.get("Dim2") or r.get("Dim3"):
            continue
        rows.append(
            dict(
                country_iso3=r["SpatialDim"],
                year=int(r["TimeDim"]),
                sex=SEX_MAP.get(dim1, "ALL"),
                age_group="ALL",
                value=float(r["NumericValue"]),
                low=r.get("Low"),
                high=r.get("High"),
                data_quality=quality,
            )
        )
    return rows


def load_who(db: Session, only: str | None = None) -> dict:
    src = get_or_create_source(db, "WHO_GHO")
    countries = {c for c in db.scalars(select(Country.iso3))}
    diseases = {d.slug: d for d in db.scalars(select(Disease))}
    report: dict = {"loaded": [], "skipped": []}

    with Run(db, "who_gho") as run:
        for cfg in WHO_INDICATORS:
            if only and only not in (cfg["slug"], cfg["disease"]):
                continue
            code = cfg["code"]
            name = official_name(code)
            if name is None or not all(k.lower() in name.lower() for k in cfg["expect"]):
                report["skipped"].append(
                    dict(slug=cfg["slug"], code=code, reason=f"name mismatch: {name!r}")
                )
                continue
            disease = diseases.get(cfg["disease"]) if cfg["disease"] else None
            ind = upsert_indicator(
                db,
                cfg["slug"],
                disease_id=disease.id if disease else None,
                source_id=src.id,
                measure=cfg["measure"],
                unit=cfg["unit"],
                name_en=cfg["name_en"],
                name_fa=cfg.get("name_fa"),
                external_code=code,
                external_name=name,
                higher_is_worse=cfg.get("higher_is_worse", True),
            )
            rows = [r for r in parse_rows(fetch_rows(code), cfg["quality"]) if r["country_iso3"] in countries]
            n = upsert_observations(db, ind.id, rows)
            run.rows += n
            report["loaded"].append(dict(slug=cfg["slug"], code=code, rows=n))
            db.commit()
    return report
