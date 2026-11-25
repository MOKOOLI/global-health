export type Phase = "no_data" | "inactive" | "sporadic" | "endemic" | "watch" | "epidemic" | "declining";

export interface PhaseDef { en: string; fa: string; desc_en: string; desc_fa: string }
export interface SurvMeta {
  phases: Record<Phase, PhaseDef>;
  patterns: Record<string, { en: string; fa: string }>;
  pattern_note: { en: string; fa: string };
  pattern_rules: { en: string; fa: string };
}
export interface Pattern {
  level: string; label: { en: string; fa: string };
  n_epidemic: number; n_watch: number; n_regions: number; n_rising: number; n_reporting: number;
  n_intro: number; share_epidemic: number; regions: string[];
}
export interface SurvDisease {
  slug: string; name: string; n_countries: number; start: string | null; end: string;
  weeks_behind_today: number; sources: string[];
}
export interface BoardRow {
  slug: string; name: string; as_of: string; weeks_behind_today: number; pattern: Pattern;
  top: { iso3: string; name: string; phase: Phase; trend: string; ratio: number | null }[];
}
export interface StatusRow {
  iso3: string; iso_numeric: string | null; name: string; who_region: string | null; phase: Phase;
  trend: "rising" | "falling" | "flat" | "unknown"; stale: boolean; last_week: string | null;
  last_value: number | null; expected: number | null; upper: number | null; ratio: number | null;
  score: number; intro: boolean; smoothed: boolean; source: string;
  r_estimate: { mean: number; low: number; high: number } | null;
}
export interface StatusResp {
  disease: string; as_of: string; dataset_start: string | null; dataset_end: string;
  weeks_behind_today: number; pattern: Pattern; rows: StatusRow[];
  generation_interval: { mean: number; sd: number } | null;
}
export interface SeriesPoint { week_start: string; value: number | null; expected: number | null; upper: number | null }
export interface Forecast {
  points: { week_start: string; value: number; low: number; high: number }[];
  reliable: boolean; model?: string;
  metrics: Record<string, unknown>;
}
export interface SeriesResp {
  iso3: string; name: string; metric: string; unit: string; as_of: string; note: string | null;
  source: { code: string; name: string };
  assessment: { phase: Phase; trend: string; ratio: number | null; score: number;
    growth: { r_week: number; time_days: number | null; significant: boolean } | null;
    r_estimate: { mean: number; low: number; high: number } | null };
  points: SeriesPoint[]; forecast: Forecast | null;
  findings: { key: string; severity: string; text_en: string; text_fa: string }[];
  smoothed?: boolean;
}

/** Phase colours: categorical, colour-blind-safe pairs; epidemic is the only saturated hue. */
export const PHASE_COLOR: Record<Phase, string> = {
  no_data: "#DCE1E5", inactive: "#EEF1F3", sporadic: "#BFD3E6", endemic: "#6E9BC4",
  watch: "#F0B550", epidemic: "#B3261E", declining: "#8E7CC3",
};
export const PHASE_ORDER: Phase[] = ["epidemic", "watch", "declining", "endemic", "sporadic", "inactive", "no_data"];

export const S_TXT = {
  fa: {
    title: "هشدار زودهنگام شیوع", disease: "بیماری", asOf: "تا هفته‌ی", timeMachine: "ماشین زمان",
    timeNote: "فقط با داده‌هایی که تا آن هفته در دسترس بود محاسبه می‌شود.",
    stale: "آخرین داده‌ی این مجموعه {n} هفته قدیمی است؛ این صفحه وضعیت امروز را نشان نمی‌دهد.",
    rules: "قاعده‌ها", countries: "کشورها", phase: "وضعیت", trend: "روند", ratio: "نسبت به حد انتظار",
    last: "آخرین هفته", rising: "صعودی", falling: "نزولی", flat: "ثابت", unknown: "نامشخص",
    pick: "یک کشور را انتخاب کنید.", forecast: "پیش‌بینی ۴ هفته", observed: "مشاهده‌شده",
    expected: "مورد انتظار", upper: "حد بالا", unreliable: "این پیش‌بینی از ساده‌ترین مدل (تکرار آخرین مقدار) بهتر نبود؛ فقط راهنمای تقریبی است.",
    reliable: "پیش‌بینی در آزمون گذشته‌نگر از مدل ساده بهتر بود.", batch: "گزارش دسته‌ای: میانگین ۴ هفته استفاده شد.",
    intro: "نخستین مورد", r: "عدد بازتولید (تقریبی)", noSeries: "داده‌ای برای نمایش نیست.",
    empty: "هنوز داده‌ی هفتگی بارگذاری نشده. دستور etl.run surv را اجرا کنید.",
    legend: "راهنما", board: "نمای کلی بیماری‌ها", reporting: "کشور گزارش‌دهنده", epi: "کشور با سیگنال",
    regions: "منطقه‌ی WHO", source: "منبع", mapLabel: "نقشه‌ی وضعیت کشورها", loading: "در حال بارگذاری…",
    table: "جدول کشورها (بر اساس شدت سیگنال)",
  },
  en: {
    title: "Outbreak early warning", disease: "Disease", asOf: "As of week", timeMachine: "Time machine",
    timeNote: "Computed using only the data that was available up to that week.",
    stale: "The newest data in this set is {n} weeks old; this page does not show today's situation.",
    rules: "Rules", countries: "Countries", phase: "Status", trend: "Trend", ratio: "vs expected limit",
    last: "Latest week", rising: "Rising", falling: "Falling", flat: "Flat", unknown: "Unknown",
    pick: "Select a country.", forecast: "4-week forecast", observed: "Observed",
    expected: "Expected", upper: "Upper limit", unreliable: "This forecast did not beat the simplest model (repeat the last value); treat it as a rough guide only.",
    reliable: "In back-testing this forecast beat the simple model.", batch: "Batch reporting detected: a 4-week mean was used.",
    intro: "First case", r: "Reproduction number (indicative)", noSeries: "No data to show.",
    empty: "No weekly data loaded yet. Run etl.run surv.",
    legend: "Legend", board: "Disease overview", reporting: "reporting countries", epi: "countries with a signal",
    regions: "WHO regions", source: "Source", mapLabel: "Country status map", loading: "Loading…",
    table: "Countries (by signal strength)",
  },
};
