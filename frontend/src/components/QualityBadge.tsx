"use client";

import { useLocale } from "@/lib/i18n";

export default function QualityBadge({ quality }: { quality: string }) {
  const { locale, label, meta } = useLocale();
  const note = meta?.data_quality[quality]?.[locale === "fa" ? "note_fa" : "note_en"];
  return (
    <span className={`q q-${quality}`} title={note}>
      {label("data_quality", quality)}
    </span>
  );
}
