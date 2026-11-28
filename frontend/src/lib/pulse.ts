export type Fresh = "fresh" | "aging" | "old";

export interface PulseWeekly {
  slug: string; name: string; as_of: string; age_days: number; freshness: Fresh; weeks_behind_today: number;
  pattern: { level: string; label: { fa: string; en: string } };
  top: { iso3: string; name: string; phase: string; trend: string; ratio: number | null }[];
}
export interface PulseAlert {
  title: string; url: string; source: string; published_at: string | null; country: string | null;
  country_iso3: string | null; disease: string | null; age_days: number | null; freshness: Fresh;
}
export interface PulseBurden {
  code: string; name: string; unit: string; measure: string; higher_is_worse: boolean; age_standardized: boolean;
  disease: string | null; disease_slug: string | null; category: string | null; year: number; n: number;
  median: number; total: number | null; extreme: { iso3: string; name: string; value: number };
  source: { code: string; name: string; synthetic: boolean } | null; age_years: number; freshness: Fresh;
}
export interface PulseJob { job: string; last_status: string; last_ok: string | null; last_ok_rows: number | null; age_hours: number | null; last_failure_message: string | null }
export interface PulseResp {
  generated_at: string; today: string; weekly: PulseWeekly[]; alerts: PulseAlert[]; burden: PulseBurden[];
  sources: PulseJob[]; thresholds: { weekly_days: number[]; alert_days: number[]; annual_years: number[] }; n_countries: number;
}
export interface PulseCountryItem {
  code: string; name: string; unit: string; measure: string; disease: string | null; disease_slug: string | null;
  year: number; value: number; low: number | null; high: number | null; quality: string | null;
  rank_worst: number; of: number; median: number; age_years: number; freshness: Fresh; higher_is_worse: boolean;
}
export interface PulseCountryResp {
  country: { iso3: string; name: string; population?: number | null }; items: PulseCountryItem[];
  alerts: { title: string; url: string; published_at: string | null }[];
}


export const PULSE_TXT = {
  fa: {
    tab: "پایش", lead: "سه ساعتِ متفاوت در یک صفحه: نظارت هفتگی، هشدارهای تازه و برآوردهای سالانه‌ی بروز و مرگ‌ومیر. هر عدد سنِ خودش را دارد؛ برآوردهای سالانه «زنده» نیستند.",
    updated: "به‌روزرسانی صفحه", refresh: "تازه‌سازی", auto: "تازه‌سازی خودکار هر ۵ دقیقه",
    fresh: "تازه", aging: "رو به کهنه", old: "کهنه",
    legendTitle: "معنای نشان تازگی",
    legendWeekly: "هفتگی: تازه تا ۱۴ روز، رو به کهنه تا ۴۵ روز", legendAlert: "هشدار: تازه تا ۷ روز، رو به کهنه تا ۳۰ روز",
    legendAnnual: "سالانه: تازه تا ۲ سال، رو به کهنه تا ۴ سال",
    weeklyTitle: "نظارت هفتگی", weeklyEmpty: "هیچ سری هفتگی‌ای بارگذاری نشده است.",
    weeklyNote: "الگوی آماری در داده‌ی گزارش‌شده؛ اعلام اپیدمی یا پاندمی کار WHO و مراجع ملی است.",
    asOf: "تا تاریخ", daysAgo: "روز پیش", topCountries: "کشورهای در صدر", openSurv: "بازکردن هشدار زودهنگام",
    alertsTitle: "تازه‌ترین هشدارهای WHO", alertsEmpty: "هشداری بارگذاری نشده است.",
    burdenTitle: "بار بیماری: آخرین برآورد هر شاخص", burdenNote: "هر ردیف آخرین سال موجود را نشان می‌دهد، نه وضعیت امروز. میانه، میانه‌ی کشورهای دارای داده است، نه میانگین جهانی.",
    search: "جست‌وجوی بیماری یا شاخص", allCats: "همه‌ی گروه‌ها", allMeasures: "همه‌ی سنجه‌ها", allFresh: "هر سنی", country: "کشور", worldwide: "همه‌ی کشورها",
    colDisease: "بیماری", colIndicator: "شاخص", colYear: "سال", colN: "کشورها", colMedian: "میانه", colTotal: "جمع کشورهای دارای داده", colExtreme: "بدترین", colAge: "سن داده", colSource: "منبع",
    colValue: "مقدار", colRange: "بازه", colRank: "رتبه (۱ = بدترین)", colWorld: "میانه‌ی کشورها",
    yearsAgo: "سال پیش", nRows: "ردیف", none: "موردی با این فیلتر نیست.", csv: "دانلود CSV", loading: "در حال بارگذاری…", failed: "پایش بارگذاری نشد",
    countryAlerts: "هشدارهای این کشور", ofN: "از",
    sourcesTitle: "منابع داده و آخرین بارگذاری", ok: "موفق", failedRun: "ناموفق", lastOk: "آخرین موفق", hoursAgo: "ساعت پیش", never: "هیچ‌وقت",
    synthetic: "داده‌ی نمونه", sort: "مرتب‌سازی",
  },
  en: {
    tab: "Pulse", lead: "Three different clocks on one page: weekly surveillance, fresh alerts, and annual incidence and mortality estimates. Every number shows its own age; annual estimates are not “live”.",
    updated: "Page updated", refresh: "Refresh", auto: "Auto-refresh every 5 minutes",
    fresh: "fresh", aging: "ageing", old: "old",
    legendTitle: "What the freshness mark means",
    legendWeekly: "Weekly: fresh up to 14 days, ageing up to 45", legendAlert: "Alerts: fresh up to 7 days, ageing up to 30",
    legendAnnual: "Annual: fresh up to 2 years, ageing up to 4",
    weeklyTitle: "Weekly surveillance", weeklyEmpty: "No weekly series are loaded.",
    weeklyNote: "A statistical pattern in reported data; declaring an epidemic or pandemic is for WHO and national authorities.",
    asOf: "as of", daysAgo: "days ago", topCountries: "Top countries", openSurv: "Open early warning",
    alertsTitle: "Latest WHO alerts", alertsEmpty: "No alerts are loaded.",
    burdenTitle: "Burden: latest estimate for each indicator", burdenNote: "Each row shows the latest year available, not today's situation. The median is the median of countries with data, not a world average.",
    search: "Search disease or indicator", allCats: "All groups", allMeasures: "All measures", allFresh: "Any age", country: "Country", worldwide: "All countries",
    colDisease: "Disease", colIndicator: "Indicator", colYear: "Year", colN: "Countries", colMedian: "Median", colTotal: "Sum over countries with data", colExtreme: "Worst", colAge: "Data age", colSource: "Source",
    colValue: "Value", colRange: "Range", colRank: "Rank (1 = worst)", colWorld: "Median of countries",
    yearsAgo: "years ago", nRows: "rows", none: "Nothing matches these filters.", csv: "Download CSV", loading: "Loading…", failed: "Pulse could not be loaded",
    countryAlerts: "Alerts for this country", ofN: "of",
    sourcesTitle: "Data sources and last load", ok: "ok", failedRun: "failed", lastOk: "last success", hoursAgo: "hours ago", never: "never",
    synthetic: "sample data", sort: "Sort",
  },
} as const;
