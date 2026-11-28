"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { SearchResp } from "@/lib/types";

interface Item { key: string; label: string; hint: string; href: string }

/** Ctrl/⌘+K (or "/") opens one box: jump to a disease, country or page, or ask a question in plain language. */
export default function CommandPalette() {
  const { locale } = useLocale();
  const fa = locale === "fa";
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [d, setD] = useState("");
  const [sel, setSel] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target as HTMLElement)?.tagName ?? "");
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) { e.preventDefault(); setOpen((o) => !o); }
      else if (e.key === "/" && !typing) { e.preventDefault(); setOpen(true); }
      else if (e.key === "Escape") setOpen(false);
    };
    const ev = () => setOpen(true);
    window.addEventListener("keydown", on); window.addEventListener("open-palette", ev);
    return () => { window.removeEventListener("keydown", on); window.removeEventListener("open-palette", ev); };
  }, []);
  useEffect(() => { if (open) { setQ(""); setSel(0); setTimeout(() => input.current?.focus(), 20); } }, [open]);
  useEffect(() => { const id = setTimeout(() => setD(q.trim()), 150); return () => clearTimeout(id); }, [q]);

  const { data } = useApi<SearchResp>(open && d.length >= 2 ? "/search" : null, { q: d, lang: locale });

  const items = useMemo<Item[]>(() => {
    const out: Item[] = [];
    if (d.length >= 2) out.push({ key: "ask", label: (fa ? "بپرس: " : "Ask: ") + d, hint: fa ? "پاسخ با منبع" : "answer with sources", href: `/${locale}/ask?q=${encodeURIComponent(d)}` });
    data?.diseases.slice(0, 6).forEach((x) => out.push({ key: "d" + x.slug, label: x.name, hint: x.icd10 ?? (fa ? "بیماری" : "disease"), href: `/${locale}/disease/${x.slug}` }));
    data?.countries.slice(0, 5).forEach((x) => out.push({ key: "c" + x.iso3, label: x.name, hint: fa ? "کشور" : "country", href: `/${locale}/country/${x.iso3}` }));
    const pages: [string, string, string][] = [
      ["surveillance", fa ? "هشدار زودهنگام" : "Early warning", "map"], ["learn", fa ? "آموزش و بازپخش" : "Learn & replay", "lessons"],
      ["viz", fa ? "نمودارهای زنده" : "Live charts", "pulse · bubbles · network · story"], ["tools", fa ? "ماشین‌حساب ASR" : "ASR calculator", "tools"], ["compare", fa ? "مقایسه" : "Compare", "countries"],
      ["resources", fa ? "منابع رسمی" : "Official resources", "WHO · CDC · PubMed"], ["data", fa ? "داده و API" : "Data & API", "licences"],
    ];
    const needle = d.toLowerCase();
    pages.filter(([, l]) => !needle || l.toLowerCase().includes(needle)).forEach(([p, l, h]) => out.push({ key: "p" + p, label: l, hint: h, href: `/${locale}/${p}` }));
    return out;
  }, [data, d, fa, locale]);

  const go = (it?: Item) => { if (it) { setOpen(false); router.push(it.href); } };
  if (!open) return null;
  return (
    <div className="palette-back" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
      <div className="palette" role="dialog" aria-modal="true" aria-label={fa ? "جست‌وجوی سریع" : "Quick search"}>
        <input ref={input} autoFocus value={q} onChange={(e) => { setQ(e.target.value); setSel(0); }} role="combobox" aria-expanded="true" aria-controls="palette-list"
          placeholder={fa ? "بیماری، کشور، یا یک پرسش…" : "Disease, country, or a question…"}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, items.length - 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
            else if (e.key === "Enter") go(items[sel]);
          }} />
        <ul id="palette-list" role="listbox">
          {items.map((it, i) => (
            <li key={it.key} role="option" aria-selected={i === sel} className={i === sel ? "on" : ""} onMouseEnter={() => setSel(i)} onClick={() => go(it)}>
              <span>{it.label}</span><span className="muted small">{it.hint}</span>
            </li>
          ))}
        </ul>
        <p className="small muted palette-foot">↑↓ Enter · Esc</p>
      </div>
    </div>
  );
}
