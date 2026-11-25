"use client";

import Link from "next/link";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { BoardRow } from "@/lib/surv";

const ORDER = ["pandemic_pattern", "novel_spread", "multi_region_outbreak", "regional_outbreak", "single_country", "watch"];

/** Live "what the data show now" strip. Always shows data age, because signals are only as fresh as the reports. */
export default function SignalStrip() {
  const { locale } = useLocale();
  const fa = locale === "fa";
  const { data } = useApi<BoardRow[]>("/surveillance/board", { lang: locale });
  if (!data) return null;
  const rows = data.filter((r) => ORDER.includes(r.pattern.level)).slice(0, 4);
  const ages = data.map((r) => r.weeks_behind_today);
  const lo = Math.min(...ages), hi = Math.max(...ages);
  const age = lo === hi ? `${lo}` : `${lo}–${hi}`;
  return (
    <section className="shell signal-strip" aria-label={fa ? "سیگنال‌های اکنون" : "Signals now"}>
      <header>
        <h2>{fa ? "داده‌ها اکنون چه نشان می‌دهند" : "What the data show now"}</h2>
        <p className="small muted">
          {fa ? `داده‌های بارگذاری‌شده ${age} هفته قدیمی‌اند. سیگنال آماری است، نه اعلام رسمی.` : `Loaded data are ${age} weeks old. A statistical signal, not an official declaration.`}
        </p>
      </header>
      {rows.length === 0 ? <p className="muted">{fa ? "هیچ الگوی هشداری در داده‌های بارگذاری‌شده نیست." : "No warning pattern in the loaded data."}</p> : (
        <ul>
          {rows.map((r) => (
            <li key={r.slug}>
              <Link href={`/${locale}/surveillance?d=${r.slug}`}>
                <strong>{r.name}</strong>
                <span>{fa ? r.pattern.label.fa : r.pattern.label.en}</span>
                <span className="small muted">{r.top.slice(0, 3).map((x) => x.name).join(" · ")}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
