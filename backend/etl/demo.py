"""SYNTHETIC demo data - for development and automated tests ONLY.

Everything written here is random numbers shaped like epidemiological series. It is flagged
`Source.is_synthetic = True`, and the API/UI show a red banner whenever synthetic data is
present. NEVER deploy a public instance with this loaded.
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Disease
from etl.common import Run, get_or_create_source, upsert_indicator, upsert_observations

DEMO_DISEASES = [
    "tuberculosis", "malaria", "hiv-aids", "measles", "diabetes", "stroke",
    "lung-cancer", "breast-cancer", "road-injuries", "depressive-disorders",
]
YEARS = range(2000, 2023)


def load_demo(db: Session, seed: int = 7, max_countries: int | None = None) -> dict:
    rng = np.random.default_rng(seed)
    src = get_or_create_source(
        db,
        "DEMO",
        name="DEMO (synthetic - NOT real data)",
        url=None,
        license="n/a",
        citation="Randomly generated for software testing.",
        is_synthetic=True,
    )
    countries = list(db.scalars(select(Country).order_by(Country.iso3)))
    if max_countries:
        countries = countries[:max_countries]
    diseases = {d.slug: d for d in db.scalars(select(Disease))}
    total = 0
    with Run(db, "demo") as run:
        for slug in DEMO_DISEASES:
            d = diseases[slug]
            for measure, scale in (("incidence", 1.0), ("mortality", 0.15)):
                ind = upsert_indicator(
                    db,
                    f"demo-{slug}-{measure}",
                    disease_id=d.id,
                    source_id=src.id,
                    measure=measure,
                    unit="per_100k",
                    name_en=f"{d.name_en} - {measure} (DEMO)",
                    name_fa=f"{d.name_fa} - {'بروز' if measure == 'incidence' else 'مرگ‌ومیر'} (نمونه)",
                    higher_is_worse=True,
                )
                rows = []
                base_global = rng.uniform(5, 400) * scale
                for c in countries:
                    level = base_global * rng.lognormal(0, 0.9)
                    drift = rng.normal(-0.012, 0.02)  # mostly slowly declining
                    jump_year = rng.choice(list(YEARS)) if rng.random() < 0.06 else None
                    for y in YEARS:
                        v = level * np.exp(drift * (y - 2000)) * rng.lognormal(0, 0.04)
                        if jump_year and y >= jump_year:
                            v *= 1.8
                        rows.append(
                            dict(
                                country_iso3=c.iso3, year=y, sex="ALL", age_group="ALL",
                                value=float(v), low=float(v * 0.85), high=float(v * 1.15),
                                data_quality="modeled",
                            )
                        )
                total += upsert_observations(db, ind.id, rows)
        run.rows = total
    return {"rows": total, "countries": len(countries)}
