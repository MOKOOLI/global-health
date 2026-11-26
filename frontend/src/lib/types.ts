export type Locale = "fa" | "en";

export interface SourceInfo {
  code: string;
  name: string;
  url?: string | null;
  license?: string | null;
  citation?: string | null;
  is_synthetic: boolean;
}

export interface IndicatorInfo {
  code: string;
  measure: string;
  unit: string;
  name: string;
  name_en: string;
  name_fa?: string | null;
  higher_is_worse: boolean;
  age_standardized: boolean;
  source: SourceInfo;
  external_code?: string | null;
  disease_slug?: string | null;
}

export interface DiseaseItem {
  slug: string;
  name: string;
  name_en: string;
  name_fa: string;
  category: string;
  icd10?: string | null;
  notifiable: boolean;
  indicator_count?: number;
}

export interface DiseaseDetail extends DiseaseItem {
  indicators: (IndicatorInfo & { latest_year: number | null; n_countries: number })[];
  default_indicator: string | null;
}

export interface MapRow {
  iso3: string;
  iso_numeric: string | null;
  name: string;
  value: number;
  low?: number | null;
  high?: number | null;
  quality: string;
  region?: string | null;
}

export interface MapResp {
  indicator: IndicatorInfo;
  year: number;
  years: number[];
  sexes: string[];
  age_groups: string[];
  breaks: number[];
  min: number;
  max: number;
  n: number;
  n_total?: number;
  population_share?: number | null;
  data: MapRow[];
}

export interface TrendPoint {
  year: number;
  value: number;
  low?: number | null;
  high?: number | null;
  quality: string;
}

export interface TrendSeries {
  iso3: string;
  name: string;
  points: TrendPoint[];
  forecast?: { method: string; points: { year: number; value: number; low: number; high: number }[] } | null;
}

export interface TrendResp {
  indicator: IndicatorInfo;
  series: TrendSeries[];
}

export interface Finding {
  key: string;
  severity: "info" | "notable" | "warning";
  text_en: string;
  text_fa: string;
}

export interface InsightsResp {
  indicator: IndicatorInfo;
  country: { iso3: string; name: string };
  findings: Finding[];
  disclaimer: string;
  synthetic: boolean;
  narrative?: { text: string; ai_generated: boolean; validated: boolean; note?: string; model?: string };
}

export interface Meta {
  measures: Record<string, { en: string; fa: string; def_en: string; def_fa: string }>;
  units: Record<string, { en: string; fa: string }>;
  data_quality: Record<string, { en: string; fa: string; note_en: string; note_fa: string }>;
  categories: Record<string, { en: string; fa: string }>;
  sexes: Record<string, { en: string; fa: string }>;
  disclaimer: { en: string; fa: string };
  sources: SourceInfo[];
  has_synthetic: boolean;
  counts: { countries: number; diseases: number; diseases_with_data?: number; indicators: number; observations: number };
}

export interface CountryItem {
  iso3: string;
  name: string;
  name_en: string;
  name_fa?: string | null;
  region?: string | null;
  income_group?: string | null;
  population?: number | null;
}

export interface ProfileItem {
  disease: DiseaseItem;
  indicator: string;
  measure: string;
  unit: string;
  year: number;
  value: number;
  low?: number | null;
  high?: number | null;
  quality: string;
  synthetic: boolean;
  higher_is_worse: boolean;
  source?: { code: string; name: string; license: string | null };
  global_median?: number;
  ratio_to_median?: number | null;
  rank?: number;
  n?: number;
}

export interface ProfileResp {
  country: { iso3: string; name: string; region?: string | null; income_group?: string | null; population?: number | null };
  items: ProfileItem[];
  generated?: string;
}

export interface Alert {
  title: string;
  url: string;
  source: string;
  published_at?: string | null;
  country_iso3?: string | null;
  summary?: string | null;
}

export interface RankingResp {
  indicator: IndicatorInfo;
  year: number;
  n: number;
  rows: { rank: number; iso3: string; name: string; region?: string | null; value: number; low?: number | null; high?: number | null; quality: string }[];
}

export interface SearchResp {
  diseases: DiseaseItem[];
  countries: { iso3: string; name: string }[];
}
