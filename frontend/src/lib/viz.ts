import type { Locale } from "./types";

export interface VizOption { code: string; name: string; unit: string; higher_is_worse: boolean; countries: number; years: number }
export interface VizOptions { indicators: VizOption[]; default: { x: string; y: string } | null }

export interface IndInfo {
  code: string; name: string; unit: string; higher_is_worse: boolean;
  source: { code: string; name: string; license: string | null };
}
export interface BubbleCountry {
  iso3: string; name: string; region: string | null; population: number | null; income: string | null;
  points: [number, number, number][]; // [year, x, y]
}
export interface BubblesResp {
  x: IndInfo; y: IndInfo; years: number[]; countries: BubbleCountry[];
  x_range: [number, number]; y_range: [number, number]; per_year: number[]; population_year: number | null;
}

export interface SimNode { iso3: string; name: string; region: string | null; cluster: number; n_indicators: number; population: number | null }
export interface SimCluster {
  id: number; size: number; examples: string[];
  features: { code: string; name: string; direction: "high" | "low"; delta: number }[];
}
export interface SimResp {
  nodes: SimNode[]; edges: { s: string; t: string; w: number }[]; clusters: SimCluster[];
  indicators: { code: string; name: string }[]; k: number; min_shared: number; method: string;
}

/** WHO regions, colour-blind-safe (Okabe-Ito based), tuned to read on the dark chart stage. */
export const REGION_COLORS: Record<string, string> = {
  AFRO: "#F0A93B", AMRO: "#56B4E9", EMRO: "#D98CB8", EURO: "#2FB38A", SEARO: "#E8DC5A", WPRO: "#8E9BFF",
};
export const REGION_FALLBACK = "#9AA9B5";
export const REGION_NAMES: Record<string, { fa: string; en: string }> = {
  AFRO: { fa: "آفریقا", en: "Africa" }, AMRO: { fa: "قاره‌ی آمریکا", en: "Americas" },
  EMRO: { fa: "مدیترانه‌ی شرقی", en: "Eastern Mediterranean" }, EURO: { fa: "اروپا", en: "Europe" },
  SEARO: { fa: "آسیای جنوب‌شرقی", en: "South-East Asia" }, WPRO: { fa: "غرب اقیانوس آرام", en: "Western Pacific" },
};
export const regionColor = (r: string | null | undefined) => (r && REGION_COLORS[r]) || REGION_FALLBACK;
export const regionName = (r: string | null | undefined, l: Locale) => (r && REGION_NAMES[r]?.[l]) || r || "—";

/** Cluster colours for the network (8 groups; beyond that, grey). */
export const CLUSTER_COLORS = ["#F0A93B", "#56B4E9", "#2FB38A", "#D98CB8", "#E8DC5A", "#8E9BFF", "#E5775A", "#7ED3D3"];
export const clusterColor = (i: number) => CLUSTER_COLORS[i] ?? REGION_FALLBACK;

export const VIZ_TXT = {
  fa: {
    title: "نمودارهای زنده", lead: "همان داده‌ی اطلس، به‌صورت متحرک و تعاملی. هر شکل فقط از مقادیر واقعاً بارگذاری‌شده ساخته می‌شود؛ چیزی تخمین یا پر نمی‌شود.",
    tabs: { pulse: "پایش", bubbles: "حباب‌های متحرک", network: "شبکه‌ی شباهت", story: "روایت زوم‌پذیر" },
    xAxis: "محور افقی", yAxis: "محور عمودی", play: "پخش", pause: "توقف", year: "سال", speed: "سرعت", log: "مقیاس لگاریتمی",
    regions: "منطقه‌ی WHO", pin: "نشان‌دار کردن کشور", pinned: "کشورهای نشان‌دار", clear: "پاک کردن", none: "—",
    sizeNote: "اندازه‌ی حباب: جمعیت کشور", sizeYear: "جمعیت یک سال ثابت است و در طول انیمیشن تغییر نمی‌کند", noPop: "برای کشورهای بدون جمعیت، حباب کوچک ثابت",
    worse: "بدتر", better: "بهتر", countriesNow: "کشور در این سال", table: "جدول داده‌ی این سال", country: "کشور",
    loading: "در حال بارگذاری…", failed: "نمودار ساخته نشد", tooFew: "برای این دو شاخص داده‌ی مشترک کافی نیست؛ شاخص‌های دیگری را امتحان کنید.",
    source: "منبع", license: "مجوز", corr: "همبستگی در نمودار به معنای علیت نیست.",
    netLead: "هر نقطه یک کشور است. کشورهایی که الگوی بار بیماری شبیه‌تری دارند به هم نزدیک‌ترند.",
    netCaveat: "این شبکه شباهت آماری گزارش‌ها را نشان می‌دهد، نه انتقال بیماری بین کشورها.",
    netHow: "روش", zoomIn: "نزدیک‌تر", zoomOut: "دورتر", reset: "بازنشانی", highlight: "پیدا کردن کشور", groups: "گروه‌ها",
    higher: "بالاتر", lower: "پایین‌تر", examples: "نمونه", members: "کشورها", similarTo: "شبیه‌ترین‌ها", openCountry: "صفحه‌ی کشور",
    indicatorsUsed: "شاخص‌های به‌کاررفته", dragHint: "بکشید، با چرخ ماوس زوم کنید",
    prev: "قبلی", next: "بعدی", auto: "پخش خودکار", scene: "صحنه", pickInd: "شاخص روایت",
    otherGroups: "{n} گروه کوچک‌تر که با رنگ خاکستری نشان داده شده‌اند.",
    storyDisclaimer: "این روایت به‌طور خودکار از داده‌های بارگذاری‌شده ساخته شده است. اعداد برآورد منبع‌اند و میانگین کشوری، نابرابری درون کشورها را پنهان می‌کند.",
  },
  en: {
    title: "Live charts", lead: "The atlas data, animated and interactive. Every shape is built only from values that are actually loaded; nothing is estimated or filled in.",
    tabs: { pulse: "Pulse", bubbles: "Animated bubbles", network: "Similarity network", story: "Zoomable story" },
    xAxis: "Horizontal axis", yAxis: "Vertical axis", play: "Play", pause: "Pause", year: "Year", speed: "Speed", log: "Logarithmic scale",
    regions: "WHO region", pin: "Pin a country", pinned: "Pinned countries", clear: "Clear", none: "—",
    sizeNote: "Bubble size: country population", sizeYear: "Population is for one fixed year and does not change during the animation", noPop: "Countries without a population get a small fixed bubble",
    worse: "worse", better: "better", countriesNow: "countries this year", table: "Data table for this year", country: "Country",
    loading: "Loading…", failed: "The chart could not be built", tooFew: "These two indicators do not share enough countries and years. Try other indicators.",
    source: "Source", license: "Licence", corr: "Correlation in a chart is not causation.",
    netLead: "Each dot is a country. Countries with a more similar disease-burden profile sit closer together.",
    netCaveat: "This network shows statistical similarity of reported figures, not disease transmission between countries.",
    netHow: "Method", zoomIn: "Zoom in", zoomOut: "Zoom out", reset: "Reset", highlight: "Find a country", groups: "Groups",
    higher: "Higher", lower: "Lower", examples: "Examples", members: "Countries", similarTo: "Most similar", openCountry: "Country page",
    indicatorsUsed: "Indicators used", dragHint: "Drag to pan, scroll to zoom",
    prev: "Previous", next: "Next", auto: "Auto-play", scene: "Scene", pickInd: "Story indicator",
    otherGroups: "{n} smaller groups, drawn in grey.",
    storyDisclaimer: "This story is generated automatically from the loaded data. Figures are the source's estimates, and a country average hides inequality within countries.",
  },
} as const;
