"use client";

import { useState } from "react";
import { useLocale } from "@/lib/i18n";

// Search-URL links only: we never claim a specific document exists, we open the authority's own search.
const SITES: { n: string; fa: string; en: string; url: (q: string) => string }[] = [
  { n: "WHO", fa: "سازمان جهانی بهداشت", en: "World Health Organization", url: (q) => `https://www.who.int/search?query=${q}` },
  { n: "CDC", fa: "مراکز کنترل و پیشگیری بیماری (آمریکا)", en: "US Centers for Disease Control", url: (q) => `https://search.cdc.gov/search/?query=${q}` },
  { n: "ECDC", fa: "مرکز اروپایی کنترل بیماری", en: "European CDC", url: (q) => `https://www.ecdc.europa.eu/en/search?s=${q}` },
  { n: "NICE", fa: "رهنمودهای بالینی بریتانیا", en: "NICE guidance (UK)", url: (q) => `https://www.nice.org.uk/search?q=${q}` },
  { n: "PubMed", fa: "مقالات پزشکی", en: "Medical literature", url: (q) => `https://pubmed.ncbi.nlm.nih.gov/?term=${q}` },
  { n: "Cochrane", fa: "مرورهای نظام‌مند", en: "Systematic reviews", url: (q) => `https://www.cochranelibrary.com/search?q=${q}` },
  { n: "GLOBOCAN", fa: "آمار سرطان (IARC)", en: "Cancer statistics (IARC)", url: () => `https://gco.iarc.fr/today` },
];
const T = {
  fa: { h: "منابع رسمی", p: "این سایت آمار را نشان می‌دهد، رهنمود بالینی نمی‌دهد. برای تصمیم درمانی به مراجع رسمی بروید. پیوندها جست‌وجوی خود آن مرجع را باز می‌کنند؛ ما وجود سند خاصی را ادعا نمی‌کنیم.", ph: "بیماری یا موضوع", open: "جست‌وجو در" },
  en: { h: "Official resources", p: "This site shows statistics; it gives no clinical guidance. For treatment decisions use the official authorities. Each link opens that authority's own search; we do not claim any particular document exists.", ph: "Disease or topic", open: "Search" },
};

export default function Resources() {
  const { locale } = useLocale();
  const t = T[locale === "fa" ? "fa" : "en"];
  const [q, setQ] = useState("");
  return (
    <div className="shell page prose">
      <h1>{t.h}</h1>
      <p>{t.p}</p>
      <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.ph} aria-label={t.ph} className="res-q" />
      <ul className="res-list">
        {SITES.map((s) => (
          <li key={s.n}><a href={s.url(encodeURIComponent(q))} target="_blank" rel="noopener noreferrer"><strong>{s.n}</strong></a>
            <span className="muted"> — {locale === "fa" ? s.fa : s.en}</span></li>
        ))}
      </ul>
    </div>
  );
}
