"""Generic loader for ANNUAL indicator CSVs (cancer registries, national statistics, GLOBOCAN-style exports...).

Nothing here assumes a particular provider's column layout: you name the columns. The source's licence and
citation are stored with the data and travel with every answer, export and snapshot.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Disease
from etl.common import Run, get_or_create_source, upsert_indicator, upsert_observations
import httpx

from etl.surveillance import _norm, country_lookup

SEX_DEFAULT = {"all": "ALL", "both": "ALL", "total": "ALL", "persons": "ALL", "male": "M", "m": "M", "men": "M", "1": "M",
               "female": "F", "f": "F", "women": "F", "2": "F", "0": "ALL"}


def _num(x: str) -> float | None:
    x = (x or "").strip().replace(",", "")
    if x in ("", "NA", "N/A", "-", "..", "null"):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def parse_annual_rows(text: str, *, country_col: str, year_col: str, value_col: str, country_kind: str = "iso3",
                      low_col: str | None = None, high_col: str | None = None, sex_col: str | None = None,
                      sex_map: dict[str, str] | None = None, filters: dict[str, str] | None = None,
                      lookup: dict | None = None, data_quality: str = "estimated") -> tuple[list[dict], list[str]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    cols = reader.fieldnames or []
    for c in (country_col, year_col, value_col):
        if c not in cols:
            raise ValueError(f"column {c!r} not in file; columns are {cols}")
    rows, unmatched = [], set()
    smap = {**SEX_DEFAULT, **{k.lower(): v for k, v in (sex_map or {}).items()}}
    for r in reader:
        if filters and any((r.get(k) or "").strip() != v for k, v in filters.items()):
            continue
        key = (r[country_col] or "").strip()
        iso = (lookup or {}).get(_norm(key)) if country_kind == "name" else key.upper()
        if country_kind == "iso2":
            iso = (lookup or {}).get(key.upper())
        if not iso:
            unmatched.add(key)
            continue
        try:
            year = int(float(r[year_col]))
        except (TypeError, ValueError):
            continue
        val = _num(r[value_col])
        if val is None:
            continue
        sex = "ALL"
        if sex_col:
            sex = smap.get((r.get(sex_col) or "").strip().lower(), "")
            if not sex:
                continue  # unknown sex label: skip rather than guess
        rows.append(dict(country_iso3=iso, year=year, sex=sex, age_group="ALL", value=val,
                         low=_num(r[low_col]) if low_col else None, high=_num(r[high_col]) if high_col else None,
                         data_quality=data_quality))
    return rows, sorted(unmatched)


def load_annual_csv(db: Session, path: str, *, source_code: str, source_name: str, license: str, citation: str,
                    disease: str, measure: str, unit: str, indicator_code: str, name_en: str, name_fa: str | None = None,
                    source_url: str | None = None, higher_is_worse: bool = True, age_standardized: bool = False, **cols) -> dict:
    d = db.scalar(select(Disease).where(Disease.slug == disease))
    if d is None:
        raise ValueError(f"unknown disease slug {disease!r}")
    text = Path(path).read_text(encoding="utf-8") if not path.startswith("http") else httpx.get(path, timeout=120).text
    kind = cols.get("country_kind", "iso3")
    lookup = None
    if kind in ("name", "iso2"):
        from app.models import Country
        lookup = country_lookup(db) if kind == "name" else {c.iso2.upper(): c.iso3 for c in db.scalars(select(Country)) if c.iso2}
    with Run(db, f"annual:{indicator_code}") as run:
        rows, unmatched = parse_annual_rows(text, lookup=lookup, **cols)
        src = get_or_create_source(db, source_code, name=source_name, url=source_url, license=license, citation=citation,
                                   is_synthetic=False)
        ind = upsert_indicator(db, indicator_code, disease_id=d.id, source_id=src.id, measure=measure, unit=unit,
                               name_en=name_en, name_fa=name_fa, higher_is_worse=higher_is_worse,
                               age_standardized=age_standardized)
        n = upsert_observations(db, ind.id, rows)
        run.rows = n
    return dict(rows=n, indicator=indicator_code, unmatched_countries=unmatched[:30], n_unmatched=len(unmatched))
