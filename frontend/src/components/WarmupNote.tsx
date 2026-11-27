"use client";

import { useEffect, useState } from "react";
import { onSlowChange } from "@/lib/api";
import { useLocale } from "@/lib/i18n";

/** Shown only while a request is slow (typically the free server waking up after idle). */
export default function WarmupNote() {
  const [slow, setSlow] = useState(false);
  const { locale } = useLocale();
  useEffect(() => onSlowChange(setSlow), []);
  if (!slow) return null;
  return (
    <p className="notice" role="status" style={{ margin: "0.5rem auto", maxWidth: "60rem" }}>
      {locale === "fa"
        ? "سرور پس از مدتی بی‌کاری در حال بیدار شدن است؛ حدود یک دقیقه صبر کنید. داده‌ها از دست نرفته‌اند."
        : "The server is waking up after being idle. This can take up to a minute; no data has been lost."}
    </p>
  );
}
