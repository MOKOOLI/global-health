"""Epidemiological vocabulary shown to clinicians (fa/en).

Incidence vs prevalence vs deaths are deliberately defined in the UI: confusing
them is the most common misreading of public-health dashboards.
"""

MEASURES: dict[str, dict] = {
    "incidence": {
        "en": "Incidence",
        "fa": "بروز",
        "def_en": "New cases arising in a population over a period (usually one year). "
        "Reflects the risk of acquiring the disease.",
        "def_fa": "تعداد موارد جدید بیماری در یک جمعیت در یک بازه زمانی (معمولاً یک سال). "
        "بیانگر خطر ابتلا است.",
    },
    "prevalence": {
        "en": "Prevalence",
        "fa": "شیوع",
        "def_en": "All existing cases (new and old) in a population at a point or during a period. "
        "Reflects the burden of living with the disease.",
        "def_fa": "همه‌ی موارد موجود (جدید و قدیمی) در یک جمعیت در یک زمان یا دوره مشخص. "
        "بیانگر بار بیماری در جمعیت است.",
    },
    "deaths": {
        "en": "Deaths",
        "fa": "مرگ",
        "def_en": "Deaths attributed to the disease in a year.",
        "def_fa": "مرگ‌های منتسب به بیماری در یک سال.",
    },
    "mortality": {
        "en": "Mortality rate",
        "fa": "نرخ مرگ‌ومیر",
        "def_en": "Deaths from the disease per 100,000 population.",
        "def_fa": "تعداد مرگ ناشی از بیماری به‌ازای هر ۱۰۰٬۰۰۰ نفر جمعیت.",
    },
    "daly": {
        "en": "DALYs",
        "fa": "DALY (سال‌های زندگی تعدیل‌شده با ناتوانی)",
        "def_en": "Disability-adjusted life years: years of life lost to premature death (YLL) "
        "plus years lived with disability (YLD).",
        "def_fa": "مجموع سال‌های زندگی از دست‌رفته به‌دلیل مرگ زودرس (YLL) و سال‌های زندگی "
        "همراه با ناتوانی (YLD).",
    },
    "cases": {
        "en": "Reported cases",
        "fa": "موارد گزارش‌شده",
        "def_en": "Cases officially notified to a surveillance system. Usually lower than true "
        "incidence because of under-diagnosis and under-reporting.",
        "def_fa": "مواردی که رسماً به نظام مراقبت گزارش شده‌اند. معمولاً کمتر از بروز واقعی است "
        "(به‌دلیل تشخیص‌داده‌نشدن و کم‌گزارشی).",
    },
    "coverage": {
        "en": "Coverage",
        "fa": "پوشش",
        "def_en": "Share of the target population reached (e.g. vaccine coverage). "
        "Higher is better.",
        "def_fa": "درصدی از جمعیت هدف که تحت پوشش قرار گرفته‌اند (مثلاً پوشش واکسن). "
        "مقدار بالاتر بهتر است.",
    },
}

UNITS: dict[str, dict] = {
    "per_100k": {"en": "per 100,000", "fa": "به‌ازای ۱۰۰٬۰۰۰ نفر"},
    "per_1000": {"en": "per 1,000", "fa": "به‌ازای ۱۰۰۰ نفر"},
    "per_100k_births": {"en": "per 100,000 live births", "fa": "به‌ازای ۱۰۰٬۰۰۰ تولد زنده"},
    "per_1000_births": {"en": "per 1,000 live births", "fa": "به‌ازای ۱۰۰۰ تولد زنده"},
    "count": {"en": "count", "fa": "تعداد"},
    "percent": {"en": "%", "fa": "درصد"},
    "years": {"en": "years", "fa": "سال"},
}

DATA_QUALITY: dict[str, dict] = {
    "reported": {
        "en": "Reported",
        "fa": "گزارش‌شده",
        "note_en": "Counted by national surveillance. May under-count in weak health systems.",
        "note_fa": "شمارش‌شده توسط نظام مراقبت ملی. در نظام‌های سلامت ضعیف ممکن است کمتر از واقع باشد.",
    },
    "estimated": {
        "en": "Estimated",
        "fa": "تخمینی",
        "note_en": "Estimated by an agency (e.g. WHO) from partial data and models.",
        "note_fa": "تخمین‌زده‌شده توسط یک سازمان (مثلاً WHO) از داده‌های ناقص و مدل‌سازی.",
    },
    "modeled": {
        "en": "Modelled",
        "fa": "مدل‌سازی‌شده",
        "note_en": "Output of a full statistical model (e.g. GBD). Treat as a best estimate with "
        "uncertainty, not a count.",
        "note_fa": "خروجی مدل آماری کامل (مثلاً GBD). به‌عنوان بهترین برآورد همراه با عدم‌قطعیت "
        "در نظر بگیرید، نه شمارش واقعی.",
    },
}

CATEGORIES: dict[str, dict] = {
    "infectious": {"en": "Infectious diseases", "fa": "بیماری‌های عفونی"},
    "neoplasms": {"en": "Cancers", "fa": "سرطان‌ها"},
    "cardiovascular": {"en": "Cardiovascular", "fa": "قلبی‌عروقی"},
    "respiratory": {"en": "Chronic respiratory", "fa": "تنفسی مزمن"},
    "metabolic": {"en": "Metabolic & renal", "fa": "متابولیک و کلیوی"},
    "neuro_mental": {"en": "Neurological, mental & substance use", "fa": "عصبی، روان‌پزشکی و مصرف مواد"},
    "musculoskeletal": {"en": "Musculoskeletal", "fa": "اسکلتی-عضلانی"},
    "skin": {"en": "Skin", "fa": "پوست"},
    "blood": {"en": "Blood disorders", "fa": "بیماری‌های خونی"},
    "eye_ear": {"en": "Eye & ear", "fa": "چشم و گوش"},
    "maternal_neonatal": {"en": "Maternal & neonatal", "fa": "مادری و نوزادی"},
    "injuries": {"en": "Injuries", "fa": "آسیب‌ها"},
    "nutritional": {"en": "Nutritional", "fa": "تغذیه‌ای"},
    "digestive": {"en": "Digestive", "fa": "گوارشی"},
    "other": {"en": "Other", "fa": "سایر"},
}

SEX_LABELS = {
    "ALL": {"en": "Both sexes", "fa": "هر دو جنس"},
    "M": {"en": "Male", "fa": "مرد"},
    "F": {"en": "Female", "fa": "زن"},
}

DISCLAIMER_EN = (
    "For epidemiological orientation only. Not a substitute for clinical judgement, "
    "national guidelines or local surveillance. Many figures are modelled estimates."
)
DISCLAIMER_FA = (
    "فقط برای آگاهی اپیدمیولوژیک. جایگزین قضاوت بالینی، رهنمودهای ملی یا مراقبت محلی نیست. "
    "بسیاری از اعداد برآورد مدل‌سازی‌شده هستند."
)
