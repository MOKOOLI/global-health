"""WHO GHO indicators to ingest.

IMPORTANT - verification guard
------------------------------
GHO indicator codes are not guessed blindly: at load time the ETL fetches the
official indicator name for each code and requires every string in `expect` to
appear in it (case-insensitive). If the code does not match, the indicator is
SKIPPED and reported - so a wrong/changed code can never silently poison the
database with the wrong disease.

Find/confirm codes with:   python -m etl.run discover tuberculosis
and add them here. Disease-specific rows reference a `disease` slug from
catalogue.py; `disease=None` means a context indicator.
"""

# (slug, disease_slug, measure, unit, who_code, name_en, name_fa, expect, higher_is_worse,
#  data_quality)
WHO_INDICATORS: list[dict] = [
    dict(slug="who-tb-incidence", disease="tuberculosis", measure="incidence", unit="per_100k",
         code="MDG_0000000020", name_en="TB incidence (per 100,000 population per year)",
         name_fa="بروز سل (به‌ازای ۱۰۰٬۰۰۰ نفر در سال)", expect=["tuberculosis", "incidence"],
         quality="estimated"),
    dict(slug="who-malaria-incidence", disease="malaria", measure="incidence", unit="per_1000",
         code="MALARIA_EST_INCIDENCE",
         name_en="Estimated malaria incidence (per 1,000 population at risk)",
         name_fa="بروز تخمینی مالاریا (به‌ازای ۱۰۰۰ نفر در معرض خطر)",
         expect=["malaria", "incidence"], quality="estimated"),
    dict(slug="who-malaria-deaths", disease="malaria", measure="deaths", unit="count",
         code="MALARIA_EST_DEATHS", name_en="Estimated number of malaria deaths",
         name_fa="تعداد تخمینی مرگ ناشی از مالاریا", expect=["malaria", "death"],
         quality="estimated"),
    dict(slug="who-hiv-prevalence-count", disease="hiv-aids", measure="prevalence", unit="count",
         code="HIV_0000000001", name_en="Estimated number of people living with HIV (all ages)",
         name_fa="تعداد تخمینی افراد زنده مبتلا به HIV (همه سنین)", expect=["living with hiv"],
         quality="estimated"),
    dict(slug="who-measles-cases", disease="measles", measure="cases", unit="count",
         code="WHS3_62", name_en="Measles - number of reported cases",
         name_fa="سرخک - تعداد موارد گزارش‌شده", expect=["measles"], quality="reported"),
    dict(slug="who-measles-vax", disease="measles", measure="coverage", unit="percent",
         code="WHS8_110", name_en="Measles-containing vaccine 1st dose (MCV1) coverage, 1-year-olds",
         name_fa="پوشش دوز اول واکسن حاوی سرخک (MCV1)، کودکان ۱ ساله",
         expect=["measles", "immunization"], higher_is_worse=False, quality="estimated"),
    dict(slug="who-dtp3-vax", disease="pertussis", measure="coverage", unit="percent",
         code="WHS4_544", name_en="DTP3 immunization coverage, 1-year-olds",
         name_fa="پوشش واکسن DTP3 (سه‌گانه)، کودکان ۱ ساله", expect=["diphtheria", "dtp3"],
         higher_is_worse=False, quality="estimated"),
    dict(slug="who-cholera-cases", disease="cholera", measure="cases", unit="count",
         code="CHOLERA_0000000001", name_en="Cholera - number of reported cases",
         name_fa="وبا - تعداد موارد گزارش‌شده", expect=["cholera"], quality="reported"),
]
