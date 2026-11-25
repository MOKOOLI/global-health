"""Data-source licence register shown on the site and returned by /api/licenses.

IMPORTANT: this is a working register, not legal advice. `verified` is False until a human has read the
provider's CURRENT terms and recorded the date. `commercial` says whether the terms, as we understand them,
allow use inside a paid service: "yes" | "check" | "no_without_permission".
"""
from __future__ import annotations

LICENSES = [
    dict(code="WHO_GHO", name="WHO Global Health Observatory", url="https://www.who.int/data/gho",
         license="CC BY-NC-SA 3.0 IGO (as we understand the WHO data terms)", commercial="check",
         note_en="A non-commercial licence may conflict with charging for a service built on this data. "
                 "Keep the free tier fully open, and get written clarification from WHO before any paid feature uses it.",
         note_fa="مجوز غیرتجاری ممکن است با دریافت پول برای سرویسی که روی این داده ساخته شده در تعارض باشد. "
                 "لایه‌ی رایگان را کاملاً باز نگه دارید و پیش از هر قابلیت پولی از WHO تأییدیه‌ی کتبی بگیرید.",
         verified=False),
    dict(code="IHME_GBD", name="IHME Global Burden of Disease", url="https://www.healthdata.org/node/822",
         license="IHME free-of-charge non-commercial user agreement", commercial="no_without_permission",
         note_en="Free use is non-commercial. Do not include GBD data in any paid tier without IHME's permission. "
                 "Cite IHME as their terms require.",
         note_fa="استفاده‌ی رایگان فقط غیرتجاری است. بدون اجازه‌ی IHME داده‌ی GBD را در هیچ لایه‌ی پولی نگذارید. "
                 "طبق شرایط IHME ارجاع دهید.",
         verified=False),
    dict(code="WORLD_BANK", name="World Bank Open Data", url="https://data.worldbank.org/summary-terms-of-use",
         license="CC BY 4.0", commercial="yes",
         note_en="Attribution required.", note_fa="ذکر منبع الزامی است.", verified=False),
    dict(code="JHU_CSSE", name="JHU CSSE COVID-19 Data (archived 2023-03-10)",
         url="https://github.com/CSSEGISandData/COVID-19", license="CC BY 4.0", commercial="yes",
         note_en="Attribution required. The repository is archived: no data after 2023-03-10.",
         note_fa="ذکر منبع الزامی است. مخزن بایگانی شده و داده‌ای پس از ۱۰ مارس ۲۰۲۳ ندارد.", verified=False),
    dict(code="OWID", name="Our World in Data (mpox)", url="https://github.com/owid/monkeypox",
         license="CC BY 4.0 (check the dataset's own licence line)", commercial="yes",
         note_en="Attribution required; underlying sources may carry their own terms.",
         note_fa="ذکر منبع الزامی است؛ منابع اصلی ممکن است شرایط خودشان را داشته باشند.", verified=False),
    dict(code="CDC", name="CDC NNDSS / FluView (via Delphi Epidata)", url="https://data.cdc.gov",
         license="US government open data; Delphi Epidata has its own terms", commercial="check",
         note_en="Read the Delphi Epidata terms and cite CDC and Delphi. Do not imply CDC endorsement.",
         note_fa="شرایط Delphi Epidata را بخوانید و CDC و Delphi را ذکر کنید. تأیید CDC را القا نکنید.", verified=False),
    dict(code="WHO_DON", name="WHO Disease Outbreak News", url="https://www.who.int/emergencies/disease-outbreak-news",
         license="WHO copyright terms", commercial="check",
         note_en="We store only titles, dates and links, and link to the original.",
         note_fa="فقط عنوان، تاریخ و پیوند ذخیره می‌شود و به منبع اصلی لینک داده می‌شود.", verified=False),
]

METHOD = dict(
    en=[
        "Annual figures come from WHO, IHME GBD or national sources and are labelled reported, estimated or modelled.",
        "Weekly early-warning signals compare each week with a baseline built only from earlier data; the 'time machine' replays history without using later data.",
        "Forecasts are 1-4 weeks ahead and shown with back-tested skill; many do not beat a naive forecast and are marked so.",
        "Signals are statistical. They are not diagnoses, treatment advice or official declarations of an epidemic or pandemic.",
    ],
    fa=[
        "آمار سالانه از WHO، IHME GBD یا منابع ملی می‌آید و با برچسب گزارش‌شده، برآوردی یا مدل‌سازی‌شده مشخص می‌شود.",
        "سیگنال‌های هفتگی هر هفته را با خط پایه‌ای مقایسه می‌کنند که فقط از داده‌های قبلی ساخته شده؛ «ماشین زمان» تاریخ را بدون استفاده از داده‌ی بعدی بازپخش می‌کند.",
        "پیش‌بینی‌ها ۱ تا ۴ هفته‌ای‌اند و با مهارت بک‌تست‌شده نمایش داده می‌شوند؛ بسیاری از آن‌ها از پیش‌بینی ساده بهتر نیستند و علامت می‌خورند.",
        "سیگنال‌ها آماری‌اند؛ تشخیص، توصیه‌ی درمانی یا اعلام رسمی اپیدمی و پاندمی نیستند.",
    ],
)
