"use client";

import { createContext, useContext, useMemo } from "react";
import { useApi } from "./api";
import type { Locale, Meta } from "./types";

const dict = {
  fa: {
    appName: "اطلس سلامت جهانی",
    tagline: "آمار بیماری‌های همه‌ی کشورها، برای پزشکان",
    nav_explore: "نقشه",
    nav_compare: "مقایسه",
    nav_about: "روش و منابع",
    search_placeholder: "جست‌وجوی بیماری، کد ICD یا کشور…",
    switch_lang: "English",
    pick_disease: "بیماری",
    filter_diseases: "فیلتر بیماری‌ها",
    all_categories: "همه‌ی گروه‌ها",
    indicator: "شاخص",
    year: "سال",
    sex: "جنس",
    no_data: "هنوز داده‌ای بارگذاری نشده",
    no_data_hint: "با اجرای دستور ETL (مثلاً etl.run who یا gbd) داده را وارد کنید.",
    no_data_for_disease: "برای این بیماری هنوز شاخصی بارگذاری نشده است.",
    legend: "راهنمای رنگ",
    no_value: "بدون داده",
    click_country: "روی یک کشور کلیک کنید تا تحلیل آن را ببینید.",
    top_countries: "بالاترین مقادیر",
    open_country: "صفحه‌ی کشور",
    open_disease: "صفحه‌ی بیماری",
    insights: "تحلیل خودکار",
    insights_note: "همه‌ی اعداد با کد محاسبه شده‌اند.",
    summarize_ai: "خلاصه با هوش مصنوعی (مدل محلی)",
    ai_label: "تولیدشده توسط هوش مصنوعی؛ اعداد با تحلیل بالا تطبیق داده شده‌اند.",
    ai_fallback: "خلاصه‌ی هوش مصنوعی در دسترس نبود یا اعتبارسنجی نشد؛ متن قالبی نمایش داده شد.",
    trend: "روند زمانی",
    forecast_label: "برون‌یابی (تقریبی)",
    source: "منبع",
    quality: "نوع داده",
    synthetic_banner:
      "هشدار: داده‌ی نمایش‌داده‌شده نمونه و ساختگی است و برای آزمایش نرم‌افزار ساخته شده. هرگز برای تصمیم بالینی استفاده نشود.",
    definitions: "تعریف‌ها",
    rank: "رتبه",
    value: "مقدار",
    ratio: "نسبت به میانه‌ی جهانی",
    disease: "بیماری",
    measure: "سنجه",
    population: "جمعیت",
    region: "منطقه",
    income: "گروه درآمدی",
    alerts: "هشدارهای اخیر شیوع",
    no_alerts: "هشداری ثبت نشده است.",
    compare_title: "مقایسه‌ی کشورها",
    add_country: "افزودن کشور",
    remove: "حذف",
    latest: "آخرین سال",
    icd10: "کد ICD-10",
    notifiable: "بیماری قابل گزارش",
    loading: "در حال بارگذاری…",
    error: "خطا در دریافت داده",
    retry: "تلاش دوباره",
    country_profile_note:
      "بیماری‌ها بر اساس نسبت مقدار این کشور به میانه‌ی جهانی مرتب شده‌اند. فقط شاخص‌های سرانه مقایسه می‌شوند.",
    all_measures: "همه‌ی سنجه‌ها",
    about_title: "روش، منابع و محدودیت‌ها",
    sources_title: "منابع داده",
    quality_title: "انواع کیفیت داده",
    how_title: "اعداد چگونه محاسبه می‌شوند؟",
    how_body:
      "روند، رتبه، نسبت به میانه، تغییر ناگهانی و برون‌یابی همگی با کد (روش‌های آماری ساده و قابل بازبینی) محاسبه می‌شوند. اگر خلاصه‌ی هوش مصنوعی فعال باشد، فقط متن همین یافته‌ها را بازنویسی می‌کند و هر عددی که در یافته‌ها نباشد باعث رد خلاصه می‌شود.",
    limits_title: "محدودیت‌ها",
    limits_body:
      "بسیاری از اعداد برآورد مدل‌سازی‌شده‌اند، نه شمارش. کشورهای با نظام ثبت ضعیف ممکن است کمتر از واقع گزارش شوند؛ «نادر بودن در آمار» به معنای «نادر بودن در عمل» نیست. مقایسه‌ی مستقیم کشورها بدون استانداردسازی سنی می‌تواند گمراه‌کننده باشد.",
    counts: "پوشش داده",
    footer_license: "کد پروژه متن‌باز است؛ داده‌ها تابع مجوز منابع خود هستند.",
    not_found: "پیدا نشد",
    year_range: "بازه",
  },
  en: {
    appName: "Global Health Atlas",
    tagline: "Disease statistics for every country, built for clinicians",
    nav_explore: "Map",
    nav_compare: "Compare",
    nav_about: "Methods & sources",
    search_placeholder: "Search disease, ICD code or country…",
    switch_lang: "فارسی",
    pick_disease: "Disease",
    filter_diseases: "Filter diseases",
    all_categories: "All groups",
    indicator: "Indicator",
    year: "Year",
    sex: "Sex",
    no_data: "No data loaded yet",
    no_data_hint: "Load data with the ETL commands (e.g. etl.run who or gbd).",
    no_data_for_disease: "No indicator has been loaded for this disease yet.",
    legend: "Colour legend",
    no_value: "No data",
    click_country: "Select a country to see its analysis.",
    top_countries: "Highest values",
    open_country: "Country page",
    open_disease: "Disease page",
    insights: "Automatic analysis",
    insights_note: "Every number is computed by code.",
    summarize_ai: "Summarise with AI (local model)",
    ai_label: "AI-generated; numbers were checked against the analysis above.",
    ai_fallback: "AI summary unavailable or failed validation; showing the template text.",
    trend: "Trend",
    forecast_label: "Extrapolation (indicative)",
    source: "Source",
    quality: "Data type",
    synthetic_banner:
      "Warning: the data shown is synthetic, generated for software testing. Never use it for clinical decisions.",
    definitions: "Definitions",
    rank: "Rank",
    value: "Value",
    ratio: "vs global median",
    disease: "Disease",
    measure: "Measure",
    population: "Population",
    region: "Region",
    income: "Income group",
    alerts: "Recent outbreak alerts",
    no_alerts: "No alerts recorded.",
    compare_title: "Compare countries",
    add_country: "Add a country",
    remove: "Remove",
    latest: "Latest year",
    icd10: "ICD-10",
    notifiable: "Notifiable disease",
    loading: "Loading…",
    error: "Could not load data",
    retry: "Try again",
    country_profile_note:
      "Diseases are ordered by this country's value relative to the global median. Only per-capita indicators are compared.",
    all_measures: "All measures",
    about_title: "Methods, sources and limits",
    sources_title: "Data sources",
    quality_title: "Types of data quality",
    how_title: "How are the numbers computed?",
    how_body:
      "Trend, rank, ratio to the median, sudden changes and extrapolation are all computed by code using simple, auditable statistics. If the AI summary is enabled it only rewrites those findings, and any number not present in the findings causes the summary to be rejected.",
    limits_title: "Limitations",
    limits_body:
      "Many figures are modelled estimates, not counts. Countries with weak registration may under-report; “rare in the statistics” does not mean “rare in practice”. Comparing countries directly without age standardisation can mislead.",
    counts: "Coverage",
    footer_license: "The code is open source; data remain under their sources' licences.",
    not_found: "Not found",
    year_range: "Range",
  },
} as const;

export type DictKey = keyof (typeof dict)["fa"];

interface Ctx {
  locale: Locale;
  dir: "rtl" | "ltr";
  t: (k: DictKey) => string;
  meta: Meta | null;
  num: (v: number | null | undefined, digits?: number) => string;
  /** locale-aware label for a measure / unit / quality / category / sex key */
  label: (group: "measures" | "units" | "data_quality" | "categories" | "sexes", key: string) => string;
}

const LocaleCtx = createContext<Ctx | null>(null);

export function LocaleProvider({ locale, children }: { locale: Locale; children: React.ReactNode }) {
  const { data: meta } = useApi<Meta>("/meta");
  const value = useMemo<Ctx>(() => {
    const nf = new Intl.NumberFormat(locale === "fa" ? "fa-IR" : "en-US", { maximumSignificantDigits: 3 });
    const nfInt = new Intl.NumberFormat(locale === "fa" ? "fa-IR" : "en-US", { maximumFractionDigits: 0 });
    return {
      locale,
      dir: locale === "fa" ? "rtl" : "ltr",
      t: (k) => dict[locale][k],
      meta,
      num: (v, digits) => {
        if (v === null || v === undefined || Number.isNaN(v)) return "—";
        if (digits === 0 || Math.abs(v) >= 1000) return nfInt.format(v);
        return nf.format(v);
      },
      label: (group, key) => {
        const g = (meta?.[group] ?? {}) as Record<string, { en: string; fa: string }>;
        return g[key]?.[locale] ?? key;
      },
    };
  }, [locale, meta]);
  return <LocaleCtx.Provider value={value}>{children}</LocaleCtx.Provider>;
}

export function useLocale(): Ctx {
  const c = useContext(LocaleCtx);
  if (!c) throw new Error("useLocale must be used inside <LocaleProvider>");
  return c;
}
