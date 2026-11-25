"""Database schema.

Design notes (important for a clinical-facing tool):
* Every observation carries its `data_quality`: reported (counted by a national
  surveillance system), estimated (modelled by WHO/UN from partial data) or
  modeled (full statistical model, e.g. GBD). Clinicians must never mistake a
  modelled number for a count.
* `Observation` is unique per (country, indicator, year, sex, age_group) so
  re-running an ETL job is idempotent.
* Diseases are anchored on ICD-10 so different sources (WHO, GBD, national
  systems) can be joined on the same disease.
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Country(Base):
    __tablename__ = "country"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    iso2: Mapped[str | None] = mapped_column(String(2))
    iso_numeric: Mapped[str | None] = mapped_column(String(3), index=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_fa: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(80), index=True)  # World Bank region
    who_region: Mapped[str | None] = mapped_column(String(8), index=True)  # AFRO/AMRO/EMRO/EURO/SEARO/WPRO
    income_group: Mapped[str | None] = mapped_column(String(60))
    population: Mapped[int | None] = mapped_column(BigInteger)
    population_year: Mapped[int | None] = mapped_column(Integer)


class Disease(Base):
    __tablename__ = "disease"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(160))
    name_fa: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(40), index=True)
    icd10: Mapped[str | None] = mapped_column(String(120))
    icd11: Mapped[str | None] = mapped_column(String(120))
    gbd_causes: Mapped[str | None] = mapped_column(Text)  # '|' separated GBD cause names
    notifiable: Mapped[bool] = mapped_column(Boolean, default=False)
    description_en: Mapped[str | None] = mapped_column(Text)
    description_fa: Mapped[str | None] = mapped_column(Text)

    indicators: Mapped[list["Indicator"]] = relationship(back_populates="disease")


class Source(Base):
    __tablename__ = "source"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(300))
    license: Mapped[str | None] = mapped_column(String(200))
    citation: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class Indicator(Base):
    __tablename__ = "indicator"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    disease_id: Mapped[int | None] = mapped_column(ForeignKey("disease.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    measure: Mapped[str] = mapped_column(String(30), index=True)
    unit: Mapped[str] = mapped_column(String(30))  # per_100k | per_1000 | count | percent | years
    name_en: Mapped[str] = mapped_column(String(300))
    name_fa: Mapped[str | None] = mapped_column(String(300))
    external_code: Mapped[str | None] = mapped_column(String(80))  # e.g. WHO GHO code
    external_name: Mapped[str | None] = mapped_column(String(400))  # official name at source
    higher_is_worse: Mapped[bool] = mapped_column(Boolean, default=True)
    age_standardized: Mapped[bool] = mapped_column(Boolean, default=False)

    disease: Mapped[Disease | None] = relationship(back_populates="indicators")
    source: Mapped[Source] = relationship()


class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (
        UniqueConstraint(
            "country_iso3", "indicator_id", "year", "sex", "age_group", name="uq_observation"
        ),
        Index("ix_obs_indicator_year", "indicator_id", "year"),
        Index("ix_obs_country_indicator", "country_iso3", "indicator_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_iso3: Mapped[str] = mapped_column(ForeignKey("country.iso3"))
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator.id"))
    year: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(8), default="ALL")  # ALL | M | F
    age_group: Mapped[str] = mapped_column(String(24), default="ALL")
    value: Mapped[float] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    data_quality: Mapped[str] = mapped_column(String(12), default="estimated")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OutbreakAlert(Base):
    __tablename__ = "outbreak_alert"
    __table_args__ = (UniqueConstraint("url", name="uq_alert_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(400))
    url: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(60))
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    country_iso3: Mapped[str | None] = mapped_column(ForeignKey("country.iso3"), index=True)
    disease_id: Mapped[int | None] = mapped_column(ForeignKey("disease.id"), index=True)
    summary: Mapped[str | None] = mapped_column(Text)


class EtlRun(Base):
    __tablename__ = "etl_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    job: Mapped[str] = mapped_column(String(60))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    rows_written: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    message: Mapped[str | None] = mapped_column(Text)


class SurveillanceSeries(Base):
    """One weekly time series: (disease, country, source, metric).

    Annual burden estimates live in `Observation`; sub-annual surveillance counts
    (reported cases per week) live here and feed the early-warning engine.
    """

    __tablename__ = "surveillance_series"
    __table_args__ = (
        UniqueConstraint("disease_id", "country_iso3", "source_id", "metric", name="uq_surv_series"),
        Index("ix_surv_disease", "disease_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    disease_id: Mapped[int] = mapped_column(ForeignKey("disease.id"))
    country_iso3: Mapped[str] = mapped_column(ForeignKey("country.iso3"))
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    metric: Mapped[str] = mapped_column(String(30), default="new_cases")  # new_cases | new_deaths | ili_pct
    unit: Mapped[str] = mapped_column(String(20), default="count")  # count | percent
    note: Mapped[str | None] = mapped_column(String(300))  # e.g. "confirmed cases only"

    disease: Mapped[Disease] = relationship()
    source: Mapped[Source] = relationship()


class SurveillanceWeekly(Base):
    __tablename__ = "surveillance_weekly"
    __table_args__ = (
        UniqueConstraint("series_id", "week_start", name="uq_surv_week"),
        Index("ix_surv_week_series", "series_id", "week_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("surveillance_series.id"))
    week_start: Mapped[date] = mapped_column(Date)  # first day of the reporting week
    value: Mapped[float] = mapped_column(Float)


class ApiKey(Base):
    """API keys are stored only as SHA-256 hashes; the plain key is shown once at creation."""
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    prefix: Mapped[str] = mapped_column(String(12))      # first chars, to identify a key in listings
    owner: Mapped[str] = mapped_column(String(200))      # e-mail or organisation
    tier: Mapped[str] = mapped_column(String(16), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
