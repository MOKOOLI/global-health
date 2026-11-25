"""Reference data: sources, diseases (ICD-10), countries (ISO 3166 + World Bank metadata)."""
from __future__ import annotations

import gettext

import pycountry
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Disease
from etl.catalogue import DISEASES, gbd_join
from etl.common import get_or_create_source, http_get_json
from etl.who_regions import WHO_REGION

SOURCES = [
    dict(
        code="WHO_GHO",
        name="WHO Global Health Observatory",
        url="https://www.who.int/data/gho",
        license="CC BY-NC-SA 3.0 IGO (check indicator page)",
        citation="World Health Organization. Global Health Observatory data repository.",
    ),
    dict(
        code="GBD",
        name="IHME Global Burden of Disease (GBD) Results",
        url="https://vizhub.healthdata.org/gbd-results/",
        license="IHME Free-of-Charge Non-commercial User Agreement (verify current terms)",
        citation="Global Burden of Disease Collaborative Network. Global Burden of Disease Study. "
        "Institute for Health Metrics and Evaluation (IHME).",
    ),
    dict(
        code="WORLD_BANK",
        name="World Bank Open Data",
        url="https://data.worldbank.org",
        license="CC BY 4.0",
        citation="World Bank. World Development Indicators.",
    ),
    dict(
        code="WHO_DON",
        name="WHO Disease Outbreak News",
        url="https://www.who.int/emergencies/disease-outbreak-news",
        license="WHO terms of use",
        citation="World Health Organization. Disease Outbreak News.",
    ),
]

# Short everyday Persian names where the ISO 3166 formal translation reads awkwardly.
FA_OVERRIDES = {
    "IRN": "ایران", "USA": "ایالات متحده آمریکا", "GBR": "بریتانیا", "RUS": "روسیه",
    "KOR": "کره جنوبی", "PRK": "کره شمالی", "SYR": "سوریه", "VNM": "ویتنام", "LAO": "لائوس",
    "BOL": "بولیوی", "VEN": "ونزوئلا", "TZA": "تانزانیا", "MDA": "مولداوی", "BRN": "برونئی",
    "COD": "جمهوری دموکراتیک کنگو", "COG": "جمهوری کنگو", "CZE": "چک", "TWN": "تایوان",
    "PSE": "فلسطین", "FSM": "میکرونزی", "MKD": "مقدونیه شمالی", "TUR": "ترکیه",
    "CIV": "ساحل عاج", "CPV": "کیپ‌ورد", "SWZ": "اسواتینی", "HKG": "هنگ‌کنگ", "MAC": "ماکائو",
    "VAT": "واتیکان", "BIH": "بوسنی و هرزگوین", "ARE": "امارات متحده عربی",
    "SAU": "عربستان سعودی", "AZE": "جمهوری آذربایجان", "BHS": "باهاما", "GMB": "گامبیا",
}

# Countries not in ISO 3166-1 / pycountry but used by health agencies.
EXTRA_COUNTRIES = [("XKX", "XK", None, "Kosovo", "کوزوو")]


def seed_sources(db: Session) -> None:
    for s in SOURCES:
        get_or_create_source(db, **s)


def seed_diseases(db: Session) -> int:
    existing = {d.slug: d for d in db.scalars(select(Disease))}
    n = 0
    for slug, en, fa, cat, icd10, notifiable, gbd in DISEASES:
        d = existing.get(slug)
        if d is None:
            d = Disease(slug=slug, name_en=en, name_fa=fa, category=cat)
            db.add(d)
        d.name_en, d.name_fa, d.category = en, fa, cat
        d.icd10, d.notifiable, d.gbd_causes = icd10, notifiable, gbd_join(gbd)
        n += 1
    db.flush()
    return n


def _fa_translator():
    try:
        return gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["fa"]).gettext
    except Exception:  # noqa: BLE001
        return lambda s: s


def seed_countries(db: Session) -> int:
    fa = _fa_translator()
    existing = {c.iso3: c for c in db.scalars(select(Country))}
    n = 0
    for c in pycountry.countries:
        name_en = getattr(c, "common_name", None) or c.name
        row = existing.get(c.alpha_3) or Country(iso3=c.alpha_3, name_en=name_en)
        row.iso2, row.iso_numeric, row.name_en = c.alpha_2, c.numeric, name_en
        translated = fa(c.name)
        row.name_fa = FA_OVERRIDES.get(c.alpha_3) or (translated if translated != c.name else None)
        db.add(row)
        n += 1
    for iso3, iso2, num, en, fa_name in EXTRA_COUNTRIES:
        row = existing.get(iso3) or Country(iso3=iso3, name_en=en)
        row.iso2, row.iso_numeric, row.name_fa = iso2, num, fa_name
        db.add(row)
        n += 1
    for c in list(existing.values()) + [r for r in db.new if isinstance(r, Country)]:
        c.who_region = WHO_REGION.get(c.iso3)
    db.flush()
    return n


def enrich_from_world_bank(db: Session) -> tuple[int, int]:
    """Add region, income group and latest population from the World Bank API."""
    meta = http_get_json(
        "https://api.worldbank.org/v2/country", {"format": "json", "per_page": 400}
    )[1]
    countries = {c.iso3: c for c in db.scalars(select(Country))}
    n_meta = 0
    for m in meta:
        c = countries.get(m["id"])
        if c is None or m["region"]["value"] == "Aggregates":
            continue
        c.region = m["region"]["value"]
        c.income_group = m["incomeLevel"]["value"]
        n_meta += 1

    pop = http_get_json(
        "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL",
        {"format": "json", "per_page": 20000, "mrnev": 1},
    )[1]
    n_pop = 0
    for p in pop or []:
        c = countries.get(p["countryiso3code"])
        if c is not None and p["value"] is not None:
            c.population, c.population_year = int(p["value"]), int(p["date"])
            n_pop += 1
    db.flush()
    return n_meta, n_pop


def seed_all(db: Session, with_world_bank: bool = True) -> dict:
    seed_sources(db)
    out = {"diseases": seed_diseases(db), "countries": seed_countries(db)}
    if with_world_bank:
        try:
            out["worldbank_meta"], out["worldbank_pop"] = enrich_from_world_bank(db)
        except Exception as e:  # noqa: BLE001
            out["worldbank_error"] = str(e)[:200]
    db.commit()
    return out
