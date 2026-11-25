"use client";

import { useMemo, useState } from "react";
import { useLocale } from "@/lib/i18n";

const T = {
  fa: { h: "فایل CSV خودتان را ببینید", p: "فایل فقط در مرورگر شما خوانده می‌شود و به هیچ سروری ارسال نمی‌شود. ستون‌های «سال» و «مقدار» را انتخاب کنید.",
    pick: "انتخاب فایل CSV", year: "ستون سال", value: "ستون مقدار", empty: "ستونی با اعداد پیدا نشد." },
  en: { h: "Plot your own CSV", p: "The file is read in your browser only and is never uploaded. Pick the year and value columns.",
    pick: "Choose a CSV file", year: "Year column", value: "Value column", empty: "No numeric columns found." },
};

function parse(text: string): string[][] {
  const rows: string[][] = []; let cur: string[] = []; let f = ""; let q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"' && text[i + 1] === '"') { f += '"'; i++; } else if (c === '"') q = false; else f += c; }
    else if (c === '"') q = true;
    else if (c === ",") { cur.push(f); f = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; cur.push(f); rows.push(cur); cur = []; f = ""; }
    else f += c;
  }
  if (f || cur.length) { cur.push(f); rows.push(cur); }
  return rows.filter((r) => r.some((x) => x.trim()));
}

export default function CsvOverlay() {
  const { locale } = useLocale();
  const t = T[locale === "fa" ? "fa" : "en"];
  const [rows, setRows] = useState<string[][]>([]);
  const [yc, setYc] = useState(0);
  const [vc, setVc] = useState(1);
  const head = rows[0] ?? [];
  const pts = useMemo(() => rows.slice(1).map((r) => [Number(r[yc]), Number(r[vc])] as const).filter(([a, b]) => Number.isFinite(a) && Number.isFinite(b)).sort((a, b) => a[0] - b[0]), [rows, yc, vc]);
  const W = 640, H = 220, P = 36;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y1 = Math.max(...ys, 0), y0 = Math.min(...ys, 0);
  const sx = (x: number) => P + ((x - x0) / (x1 - x0 || 1)) * (W - 2 * P);
  const sy = (y: number) => H - P - ((y - y0) / (y1 - y0 || 1)) * (H - 2 * P);
  return (
    <section className="csv-overlay">
      <h2>{t.h}</h2>
      <p>{t.p}</p>
      <input type="file" accept=".csv,text/csv" aria-label={t.pick}
        onChange={async (e) => { const f = e.target.files?.[0]; if (f) { const r = parse((await f.text()).replace(/^﻿/, "")); setRows(r); setYc(0); setVc(Math.min(1, (r[0]?.length ?? 1) - 1)); } }} />
      {head.length > 0 && (
        <>
          <div className="tool-row">
            <label>{t.year} <select value={yc} onChange={(e) => setYc(Number(e.target.value))}>{head.map((h, i) => <option key={i} value={i}>{h}</option>)}</select></label>
            <label>{t.value} <select value={vc} onChange={(e) => setVc(Number(e.target.value))}>{head.map((h, i) => <option key={i} value={i}>{h}</option>)}</select></label>
          </div>
          {pts.length < 2 ? <p className="muted">{t.empty}</p> : (
            <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${head[vc]} / ${head[yc]}`} className="csv-chart" style={{ direction: "ltr" }}>
              <line x1={P} x2={W - P} y1={sy(0)} y2={sy(0)} stroke="var(--line)" />
              <polyline fill="none" stroke="var(--ui)" strokeWidth="2" points={pts.map(([a, b]) => `${sx(a)},${sy(b)}`).join(" ")} />
              {pts.map(([a, b], i) => <circle key={i} cx={sx(a)} cy={sy(b)} r="2.5" fill="var(--ui)" />)}
              <text x={P} y={H - 8} fontSize="11" fill="var(--muted)">{x0}</text>
              <text x={W - P} y={H - 8} fontSize="11" fill="var(--muted)" textAnchor="end">{x1}</text>
              <text x={4} y={sy(y1) + 4} fontSize="11" fill="var(--muted)">{y1}</text>
            </svg>
          )}
        </>
      )}
    </section>
  );
}
