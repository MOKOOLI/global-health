"use client";

import MapNote from "./MapNote";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { PHASE_COLOR, type Phase } from "@/lib/surv";
import { loadGeo, type Geo } from "./WorldMap";

interface Frames {
  phase_codes: Phase[]; countries: string[]; numeric: (string | null)[]; weeks: string[]; codes: number[][];
  levels: { level: string; n_epidemic: number; n_regions: number; n_reporting: number }[];
  names: string[] | { en: string[]; fa: string[] };
  patterns?: Record<string, { en: string; fa: string }>;
  attribution?: string;
}

const FALLBACK_PATTERNS: Record<string, { en: string; fa: string }> = {
  none: { en: "No signal", fa: "بدون سیگنال" }, watch: { en: "Watch", fa: "تحت نظر" },
  single_country: { en: "Single-country outbreak", fa: "شیوع در یک کشور" },
  regional_outbreak: { en: "Regional outbreak", fa: "شیوع منطقه‌ای" },
  novel_spread: { en: "Novel spread across regions", fa: "گسترش نوپدید در چند منطقه" },
  multi_region_outbreak: { en: "Multi-region outbreak", fa: "شیوع چندمنطقه‌ای" },
  pandemic_pattern: { en: "Pandemic-like pattern", fa: "الگوی شبه‌پاندمیک" },
};

const TXT = {
  fa: { link: "کپی پیوند این هفته", embed: "کپی کد جاسازی", svg: "دانلود SVG", copied: "کپی شد", play: "پخش", pause: "توقف", week: "هفته", countries: "کشور با سیگنال", regions: "منطقه‌ی WHO",
        reporting: "کشور گزارش‌دهنده", loading: "در حال بارگذاری بازپخش…", fail: "داده‌ی بازپخش در دسترس نیست.",
        scrub: "هفته", legend: ["بدون داده", "بی‌فعالیت", "پراکنده", "اندمیک", "تحت نظر", "بالاتر از حد انتظار", "فروکش"] },
  en: { link: "Copy link to this week", embed: "Copy embed code", svg: "Download SVG", copied: "Copied", play: "Play", pause: "Pause", week: "Week", countries: "countries with a signal", regions: "WHO regions",
        reporting: "reporting countries", loading: "Loading replay…", fail: "Replay data is unavailable.",
        scrub: "Week", legend: ["No data", "Inactive", "Sporadic", "Endemic", "Watch", "Above expected", "Declining"] },
};

const DARK_FILL: Partial<Record<Phase, string>> = { no_data: "#2B4358", inactive: "#1F3649", sporadic: "#7FA6C9", endemic: "#5C8DB8" };

export default function ReplayPlayer({ slug, locale, autoplay = false, dark = false, caption, from, to, step = 3, startWeek, share = false }: {
  slug: string; locale: "fa" | "en"; autoplay?: boolean; dark?: boolean; caption?: string;
  /** Optional ISO date window: only weeks inside [from, to] are shown. */
  from?: string; to?: string; step?: number;
  /** Open at this ISO week (nearest earlier frame); used by share links. */
  startWeek?: string;
  /** Show copy-link, embed-code and SVG-download buttons. */
  share?: boolean;
}) {
  const T = TXT[locale];
  const [f, setF] = useState<Frames | null>(null);
  const [geo, setGeo] = useState<Geo[]>([]);
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [err, setErr] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { loadGeo().then(setGeo).catch(() => setGeo([])); }, []);
  useEffect(() => {
    let dead = false;
    setF(null); setErr(false); setPlaying(false);
    const live = api<Frames>(`/surveillance/${slug}/frames`, { step, lang: locale });
    live.catch(() => fetch(`/demo/${slug}-replay.json`).then((r) => { if (!r.ok) throw new Error(); return r.json() as Promise<Frames>; }))
      .then((d) => {
        if (dead) return;
        if (from || to) {
          const keep = d.weeks.map((w, k) => (!from || w >= from) && (!to || w <= to) ? k : -1).filter((k) => k >= 0);
          if (keep.length > 1) d = { ...d, weeks: keep.map((k) => d.weeks[k]), codes: keep.map((k) => d.codes[k]), levels: keep.map((k) => d.levels[k]) };
        }
        let first = 0;
        if (startWeek) { const k = d.weeks.filter((w) => w <= startWeek).length - 1; if (k > 0) first = k; }
        setF(d); setI(first);
        const calm = typeof window !== "undefined" && (window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.dataset.lite === "1");
        if (autoplay && !calm && !startWeek) setPlaying(true);
      })
      .catch(() => !dead && setErr(true));
    return () => { dead = true; };
  }, [slug, locale, autoplay, from, to, step, startWeek]);

  const n = f?.weeks.length ?? 0;
  useEffect(() => {
    if (timer.current) clearInterval(timer.current);
    if (!playing || !n) return;
    timer.current = setInterval(() => setI((k) => {
      if (k >= n - 1) { setPlaying(false); return k; }
      return k + 1;
    }), 140);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [playing, n]);

  const byNumeric = useMemo(() => {
    const m = new Map<string, number>();
    f?.numeric.forEach((x, k) => { if (x) m.set(x, k); });
    return m;
  }, [f]);
  const names = f ? (Array.isArray(f.names) ? f.names : f.names[locale]) : [];
  const [tip, setTip] = useState<{ t: string; x: number; y: number } | null>(null);
  const [note, setNote] = useState("");
  const svgRef = useRef<SVGSVGElement | null>(null);
  const toggle = useCallback(() => { if (i >= n - 1) setI(0); setPlaying((p) => !p); }, [i, n]);

  if (err) return <p className="muted small">{T.fail}</p>;
  if (!f) return <div className={`replay${dark ? " dark" : ""}`}><p className="muted small" style={{ padding: 24 }}>{T.loading}</p></div>;
  const lv = f.levels[i];
  const patterns = f.patterns ?? FALLBACK_PATTERNS;
  const label = (patterns[lv.level] ?? FALLBACK_PATTERNS[lv.level] ?? { en: lv.level, fa: lv.level })[locale];
  const row = f.codes[i];
  return (
    <figure className={`replay${dark ? " dark" : ""}`}>
      <div className="replay-readout" aria-live="off">
        <div>
          <span className="replay-week" dir="ltr">{f.weeks[i]}</span>
          <strong className={`replay-level lvl-${lv.level}`}>{label}</strong>
        </div>
        <span className="replay-count">
          {lv.n_epidemic.toLocaleString(locale === "fa" ? "fa" : "en")} {T.countries} · {lv.n_regions.toLocaleString(locale === "fa" ? "fa" : "en")} {T.regions}
        </span>
      </div>
      <div className="replay-map">
        <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 500" role="img" aria-label={caption ?? label} className="map-svg">
          {geo.map((g) => {
            const k = byNumeric.get(g.id);
            const ph = k === undefined ? "no_data" : (f.phase_codes[row[k]] as Phase);
            return (
              <path key={g.id} d={g.d} fill={(dark && DARK_FILL[ph]) || PHASE_COLOR[ph]} className="rc"
                onMouseMove={(e) => {
                  const b = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                  setTip({ t: `${k === undefined ? g.name : names[k]} · ${T.legend[row[k ?? 0] ?? 0]}`, x: e.clientX - b.left, y: e.clientY - b.top });
                }}
                onMouseLeave={() => setTip(null)} />
            );
          })}
        </svg>
        {tip && <div className="map-tip" style={{ insetInlineStart: tip.x + 12, top: tip.y + 12 }}>{tip.t}</div>}
      </div>
      <div className="replay-bar">
        <button className="replay-btn" onClick={toggle} aria-label={playing ? T.pause : T.play}>
          {playing ? "❚❚" : "▶"}
        </button>
        <input type="range" min={0} max={n - 1} value={i} onChange={(e) => { setPlaying(false); setI(Number(e.target.value)); }}
          aria-label={T.scrub} aria-valuetext={f.weeks[i]} />
      </div>
      <ul className="legend replay-legend">
        {[5, 4, 6, 3, 2].map((c) => (
          <li key={c}><i style={{ background: (dark && DARK_FILL[f.phase_codes[c]]) || PHASE_COLOR[f.phase_codes[c]] }} />{T.legend[c]}</li>
        ))}
      </ul>
      {share && (
        <div className="replay-share">
          {([
            [T.link, () => `${location.origin}/${locale}/learn?lesson=${slug}&week=${f.weeks[i]}`],
            [T.embed, () => `<iframe src="${location.origin}/${locale}/embed/${slug}?week=${f.weeks[i]}${from ? `&from=${from}` : ""}${to ? `&to=${to}` : ""}" width="100%" height="560" style="border:0" loading="lazy" title="Global Health Atlas replay"></iframe>`],
          ] as [string, () => string][]).map(([label, make]) => (
            <button key={label} type="button" className="btn-quiet" onClick={() => { navigator.clipboard?.writeText(make()).then(() => { setNote(T.copied); setTimeout(() => setNote(""), 1800); }); }}>{label}</button>
          ))}
          <button type="button" className="btn-quiet" onClick={() => {
            const el = svgRef.current; if (!el) return;
            const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(el)], { type: "image/svg+xml" }));
            const a = document.createElement("a"); a.href = url; a.download = `${slug}-${f.weeks[i]}.svg`; a.click(); URL.revokeObjectURL(url);
          }}>{T.svg}</button>
          <span role="status" className="small muted">{note}</span>
        </div>
      )}
      <MapNote />
      {f.attribution && <figcaption className="small muted">{f.attribution}</figcaption>}
    </figure>
  );
}
