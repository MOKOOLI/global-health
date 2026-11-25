export interface AskItem {
  indicator: {
    code: string; name_en: string; name_fa: string | null; measure: string; unit: string; external_code: string | null;
    source: { code: string; name: string; url: string | null; license: string | null; citation: string | null; is_synthetic: boolean };
  };
  country: { iso3: string; name: string; name_fa: string | null };
  requested_year: number | null; year: number; year_exact: boolean; sex: string;
  value: number; low: number | null; high: number | null; quality: string; retrieved_at: string | null;
  text: string;
  links: { disease: string; csv: string; cite: { kind: "indicator"; key: string } };
}
export interface AskResp {
  question: string; lang: "fa" | "en";
  status: "answered" | "partial" | "no_data" | "needs_clarification" | "out_of_scope" | "not_understood";
  interpretation: {
    disease?: { slug: string; name: string }[]; country?: { iso3: string; name: string } | null;
    years?: number[]; latest?: boolean; measures?: string[]; sex?: string;
    typo_corrections?: { kind: string; heard: string; matched: string; score: number }[];
  };
  items: AskItem[];
  warnings: { code: string; text: string; severity?: string }[];
  candidates: { diseases?: { slug: string; name: string }[] };
  message: string; method: string;
}

export const ASK_TXT = {
  fa: {
    title: "پرسش هوشمند", lead: "سؤال خود را بنویسید یا بگویید. پاسخ فقط از پایگاه داده و همراه با منبع و مجوز می‌آید.",
    placeholder: "مثلاً: آمار سرطان سینه در انگلیس سال ۲۰۲۰ چقدر بوده؟", ask: "بپرس", mic: "گفتن سؤال", stop: "توقف",
    listening: "در حال گوش دادن…", unsupported: "مرورگر شما تشخیص گفتار را پشتیبانی نمی‌کند (Chrome، Edge یا Safari را امتحان کنید).",
    micPrivacy: "تشخیص گفتار توسط مرورگر انجام می‌شود و صدا ممکن است به سرویس سازنده‌ی مرورگر (مثلاً گوگل در Chrome) فرستاده شود.",
    micDenied: "دسترسی به میکروفون داده نشد.", voiceLang: "زبان گفتار", examples: "نمونه‌ها",
    understood: "این‌طور فهمیدم", disease: "بیماری", country: "کشور", year: "سال", measure: "شاخص", latest: "آخرین سال موجود",
    evidence: "مدرک", source: "منبع", license: "مجوز", retrieved: "زمان دریافت", indicator: "شاخص", range: "بازه",
    openPage: "صفحه‌ی بیماری", how: "چطور پاسخ داده شد", pick: "کدام را می‌گویید؟", none: "پاسخی یافت نشد.",
    synthetic: "داده‌ی ساختگی", year_ne: "سال مورد نظر موجود نبود", thinking: "در حال جست‌وجو…",
    exs: ["آمار سرطان سینه در انگلیس سال ۲۰۲۰ چقدر بوده؟", "بروز سل در هند ۲۰۱۹", "مرگ ناشی از دیابت در ایران", "breast cancer incidence in the UK 2020"],
    privacy: "پرسش شما برای پاسخ‌دادن به سرور فرستاده می‌شود؛ هیچ اطلاعات بیمار را در آن ننویسید.",
  },
  en: {
    title: "Ask", lead: "Type or say your question. Answers come only from the database, with source and licence.",
    placeholder: "For example: How many breast cancer cases in the UK in 2020?", ask: "Ask", mic: "Speak your question", stop: "Stop",
    listening: "Listening…", unsupported: "Your browser does not support speech recognition (try Chrome, Edge or Safari).",
    micPrivacy: "Speech recognition is done by your browser; the audio may be sent to the browser vendor's service (for example Google in Chrome).",
    micDenied: "Microphone access was not granted.", voiceLang: "Speech language", examples: "Examples",
    understood: "How I understood it", disease: "Disease", country: "Country", year: "Year", measure: "Measure", latest: "latest available year",
    evidence: "Evidence", source: "Source", license: "Licence", retrieved: "Retrieved", indicator: "Indicator", range: "Range",
    openPage: "Disease page", how: "How this was answered", pick: "Which one do you mean?", none: "No answer found.",
    synthetic: "synthetic data", year_ne: "the requested year was not available", thinking: "Searching…",
    exs: ["How many breast cancer cases in the UK in 2020?", "TB incidence India 2019", "diabetes deaths in Iran", "آمار سرطان سینه در انگلیس ۲۰۲۰"],
    privacy: "Your question is sent to the server to be answered; do not type any patient information.",
  },
};
