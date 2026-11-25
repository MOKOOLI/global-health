"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { SearchResp } from "@/lib/types";
import ThemeToggle from "./ThemeToggle";

function SearchBox() {
  const { locale, t } = useLocale();
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(q.trim()), 200);
    return () => clearTimeout(id);
  }, [q]);

  const { data } = useApi<SearchResp>(debounced.length >= 2 ? "/search" : null, { q: debounced, lang: locale });
  const has = data && (data.diseases.length > 0 || data.countries.length > 0);

  return (
    <div className="search" onBlur={() => setTimeout(() => setOpen(false), 150)}>
      <input
        type="search"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={t("search_placeholder")}
        aria-label={t("search_placeholder")}
      />
      {open && debounced.length >= 2 && has && (
        <ul className="search-results">
          {data!.diseases.map((d) => (
            <li key={d.slug}>
              <Link href={`/${locale}/disease/${d.slug}`} onClick={() => setQ("")}>
                {d.name} <span className="muted small">{d.icd10}</span>
              </Link>
            </li>
          ))}
          {data!.countries.map((c) => (
            <li key={c.iso3}>
              <Link href={`/${locale}/country/${c.iso3}`} onClick={() => setQ("")}>
                {c.name} <span className="muted small">{c.iso3}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Header() {
  const { locale, t } = useLocale();
  const path = usePathname() ?? `/${locale}`;
  const other = locale === "fa" ? "en" : "fa";
  const switched = path.replace(/^\/(fa|en)/, `/${other}`);
  const nav = [
    { href: `/${locale}/explore`, label: t("nav_explore"), active: path.startsWith(`/${locale}/explore`) || path.startsWith(`/${locale}/disease`) || path.startsWith(`/${locale}/country`) },
    { href: `/${locale}/ask`, label: locale === "fa" ? "پرسش" : "Ask", active: path.startsWith(`/${locale}/ask`) },
    { href: `/${locale}/surveillance`, label: locale === "fa" ? "هشدار زودهنگام" : "Early warning", active: path.startsWith(`/${locale}/surveillance`) },
    { href: `/${locale}/learn`, label: locale === "fa" ? "آموزش" : "Learn", active: path.startsWith(`/${locale}/learn`) },
    { href: `/${locale}/compare`, label: t("nav_compare"), active: path.startsWith(`/${locale}/compare`) },
    { href: `/${locale}/tools`, label: locale === "fa" ? "ابزارها" : "Tools", active: path.startsWith(`/${locale}/tools`) },
    { href: `/${locale}/data`, label: locale === "fa" ? "داده و مجوزها" : "Data & API", active: path.startsWith(`/${locale}/data`) },
    { href: `/${locale}/about`, label: t("nav_about"), active: path.startsWith(`/${locale}/about`) },
  ];
  return (
    <header className="site-header">
      <div className="shell header-row">
        <Link href={`/${locale}`} className="wordmark">
          {t("appName")}
        </Link>
        <nav aria-label="main">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} aria-current={n.active ? "page" : undefined}>
              {n.label}
            </Link>
          ))}
        </nav>
        <SearchBox />
        <button type="button" className="kbd-btn" onClick={() => window.dispatchEvent(new Event("open-palette"))} aria-label="Quick search (Ctrl+K)">⌘K</button>
        <ThemeToggle />
        <Link href={switched} className="lang" hrefLang={other} lang={other}>
          {t("switch_lang")}
        </Link>
      </div>
    </header>
  );
}
