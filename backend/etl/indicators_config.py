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
         code="WHS4_100", name_en="DTP3 immunization coverage, 1-year-olds",
         name_fa="پوشش واکسن DTP3 (سه‌گانه)، کودکان ۱ ساله", expect=["dtp3", "immunization"],
         higher_is_worse=False, quality="estimated"),
    dict(slug="who-cholera-cases", disease="cholera", measure="cases", unit="count",
         code="CHOLERA_0000000001", name_en="Cholera - number of reported cases",
         name_fa="وبا - تعداد موارد گزارش‌شده", expect=["cholera"], quality="reported"),
    dict(slug="who-polio-cases", disease="polio", measure="cases", unit="count",
         code="WHS3_49", name_en="Poliomyelitis - number of reported cases",
         name_fa="فلج اطفال - تعداد موارد گزارش‌شده", expect=["poliomyelitis", "cases"], quality="reported"),
    dict(slug="who-diabetes-prevalence-asr", disease="diabetes", measure="prevalence", unit="percent",
         code="NCD_DIABETES_PREVALENCE_AGESTD", name_en="Diabetes prevalence, adults, age-standardized",
         name_fa="شیوع دیابت در بزرگسالان (استانداردشده بر اساس سن)",
         expect=["prevalence of diabetes", "age-standardized"], quality="estimated",
         dim2="AGEGROUP_YEARS18-PLUS"),   # WHO publishes sex-specific rows for 30+, so only the 18+ both-sexes series is comparable
    dict(slug="who-hypertension-prevalence-asr", disease="hypertension", measure="prevalence", unit="percent",
         code="NCD_HYP_PREVALENCE_A", name_en="Hypertension prevalence, adults 30-79, age-standardized",
         name_fa="شیوع فشارخون بالا در ۳۰ تا ۷۹ سال (استانداردشده بر اساس سن)",
         expect=["hypertension", "prevalence", "age-standardized"], quality="estimated"),
    dict(slug="who-suicide-asr", disease="suicide", measure="mortality", unit="per_100k",
         code="MH_12", name_en="Suicide mortality rate, age-standardized",
         name_fa="نرخ مرگ ناشی از خودکشی (استانداردشده بر اساس سن)",
         expect=["suicide", "age-standardized"], quality="estimated"),
    dict(slug="who-maternal-mortality", disease="maternal-disorders", measure="mortality", unit="per_100k_births",
         code="MDG_0000000026", name_en="Maternal mortality ratio (per 100,000 live births)",
         name_fa="نسبت مرگ مادران (به‌ازای ۱۰۰٬۰۰۰ تولد زنده)", expect=["maternal mortality ratio"], quality="estimated"),
    dict(slug="who-neonatal-mortality", disease="neonatal-disorders", measure="mortality", unit="per_1000_births",
         code="WHOSIS_000003", name_en="Neonatal mortality rate (per 1,000 live births)",
         name_fa="نرخ مرگ نوزادان (به‌ازای ۱۰۰۰ تولد زنده)", expect=["neonatal mortality rate"], quality="estimated", dim2="AGEGROUP_DAYS0-27"),
    dict(slug="who-road-death-rate", disease="road-injuries", measure="mortality", unit="per_100k",
         code="RS_198", name_en="Estimated road traffic death rate",
         name_fa="نرخ تخمینی مرگ ناشی از تصادفات جاده‌ای", expect=["road traffic death rate"], quality="estimated"),
    dict(slug="who-breast-cancer-death-asr", disease="breast-cancer", measure="mortality", unit="per_100k",
         code="SA_0000001438", name_en="Breast cancer death rate, age-standardized",
         name_fa="نرخ مرگ ناشی از سرطان پستان (استانداردشده بر اساس سن)",
         expect=["death rates", "breast cancer"], quality="estimated"),
    dict(slug="who-colorectal-cancer-death-asr", disease="colorectal-cancer", measure="mortality", unit="per_100k",
         code="SA_0000001439", name_en="Colorectal cancer death rate, age-standardized",
         name_fa="نرخ مرگ ناشی از سرطان روده بزرگ (استانداردشده بر اساس سن)",
         expect=["death rates", "colon and rectum"], quality="estimated"),
    dict(slug="who-liver-cancer-death-asr", disease="liver-cancer", measure="mortality", unit="per_100k",
         code="SA_0000001445", name_en="Liver cancer death rate, age-standardized",
         name_fa="نرخ مرگ ناشی از سرطان کبد (استانداردشده بر اساس سن)",
         expect=["death rates", "liver cancer"], quality="estimated"),
    dict(slug="who-oesophageal-cancer-death-asr", disease="oesophageal-cancer", measure="mortality", unit="per_100k",
         code="SA_0000001449", name_en="Oesophageal cancer death rate, age-standardized",
         name_fa="نرخ مرگ ناشی از سرطان مری (استانداردشده بر اساس سن)",
         expect=["death rates", "oesophagus"], quality="estimated"),
]
