"""Shared DB query helpers."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Country, Disease, Indicator, Observation, Source


def get_indicator(db: Session, code: str) -> Indicator | None:
    return db.scalar(select(Indicator).where(Indicator.code == code))


def years_available(db: Session, indicator_id: int, sex="ALL", age="ALL") -> list[int]:
    q = (
        select(Observation.year)
        .where(
            Observation.indicator_id == indicator_id,
            Observation.sex == sex,
            Observation.age_group == age,
        )
        .distinct()
        .order_by(Observation.year)
    )
    return list(db.scalars(q))


def latest_year(db: Session, indicator_id: int, sex="ALL", age="ALL") -> int | None:
    return db.scalar(
        select(func.max(Observation.year)).where(
            Observation.indicator_id == indicator_id,
            Observation.sex == sex,
            Observation.age_group == age,
        )
    )


def series(db: Session, indicator_id: int, iso3: str, sex="ALL", age="ALL") -> list[Observation]:
    return list(
        db.scalars(
            select(Observation)
            .where(
                Observation.indicator_id == indicator_id,
                Observation.country_iso3 == iso3,
                Observation.sex == sex,
                Observation.age_group == age,
            )
            .order_by(Observation.year)
        )
    )


def year_slice(db: Session, indicator_id: int, year: int, sex="ALL", age="ALL"):
    return list(
        db.execute(
            select(Observation, Country)
            .join(Country, Country.iso3 == Observation.country_iso3)
            .where(
                Observation.indicator_id == indicator_id,
                Observation.year == year,
                Observation.sex == sex,
                Observation.age_group == age,
            )
        )
    )


def has_synthetic(db: Session) -> bool:
    return bool(db.scalar(select(func.count()).select_from(Source).where(Source.is_synthetic)))


def indicator_dict(ind: Indicator, lang: str = "en") -> dict:
    return dict(
        code=ind.code,
        measure=ind.measure,
        unit=ind.unit,
        name=(ind.name_fa if lang == "fa" and ind.name_fa else ind.name_en),
        name_en=ind.name_en,
        name_fa=ind.name_fa,
        higher_is_worse=ind.higher_is_worse,
        age_standardized=ind.age_standardized,
        source=dict(
            code=ind.source.code,
            name=ind.source.name,
            url=ind.source.url,
            license=ind.source.license,
            citation=ind.source.citation,
            is_synthetic=ind.source.is_synthetic,
        ),
        external_code=ind.external_code,
        disease_slug=ind.disease.slug if ind.disease else None,
    )


def disease_dict(d: Disease, lang: str = "en") -> dict:
    return dict(
        slug=d.slug,
        name=d.name_fa if lang == "fa" else d.name_en,
        name_en=d.name_en,
        name_fa=d.name_fa,
        category=d.category,
        icd10=d.icd10,
        notifiable=d.notifiable,
    )
