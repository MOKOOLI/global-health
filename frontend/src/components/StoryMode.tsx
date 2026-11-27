"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { scaleThreshold } from "d3-scale";
import { feature } from "topojson-client";
import { api, useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { MapResp, MapRow } from "@/lib/types";
import { VIZ_TXT, type VizOptions } from "@/lib/viz";
import { NO_DATA, RAMP_BURDEN, RAMP_GOOD } from "./WorldMap";

const W = 960, H = 500;
interface Shape { id: string; name: string; d: string; bbox: [[number, number], [number, number]]; c: [number, number] }
interface Scene { id: string; title: string; text: string; target: string[] | null; mark: string[]; dimOthers?: boolean }

let shapesCache: Promise<Shape[]> | null = null;
function loadShapes(): Promise<Shape[]> {
  if (!shapesCache) {
    shapesCache = fetch("/countries-110m.json").then((r) => r.json()).then((topo) => {
      const fc = feature(topo, topo.objects.countries) as unknown as { features: { id?: string | number; properties: { name: string } }[] };
      const path = geoPath(geoNaturalEarth1().fitSize([W, H], { type: "Sphere" }));
      return fc.features.filter((f) => String(f.id) !== "010").map((f) => ({
        id: String(f.id ?? "").padStart(3, "0"), name: f.properties.name, d: path(f as never) ?? "",
        bbox: path.bounds(f as never) as Shape["bbox"], c: path.centroid(f as never) as [number, number],
      }));
    });
  }
  return shapesCache;
}

const median = (v: number[]) => { const s = [...v].sort((a, b) => a - b); const n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : NaN; };

export default function StoryMode() {
  const { locale, num, label, dir } = useLocale();
  const T = VIZ_TXT[locale];
  const fa = locale === "fa";
  const opts = useApi<VizOptions>("/viz/options", { lang: locale });
  const [code, setCode] = useState<string | null>(null);
  useEffect(() => { if (opts.data?.default && !code) setCode(opts.data.default.y); }, [opts.data, code]);

  const [shapes, setShapes] = useState<Shape[]>([]);
  const [data, setData] = useState<{ now: MapResp; base: MapResp | null } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [i, setI] = useState(0);
  const [auto, setAuto] = useState(false);
  const [reduced, setReduced] = useState(false);
  const root = useRef<HTMLDivElement | null>(null);

  useEffect(() => { loadShapes().then(setShapes).catch(() => setShapes([])); }, []);
  useEffect(() => {
    const m = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(m.matches);
  }, []);

  useEffect(() => {
    if (!code) return;
    let off = false;
    setData(null); setErr(null); setI(0);
    (async () => {
      try {
        const now = await api<MapResp>(`/indicators/${code}/map`, { lang: locale });
        const ys = now.years.filter((y) => y <= now.year - 10);
        const by = ys.length ? ys[ys.length - 1] : now.years[0];
        const base = by < now.year ? await api<MapResp>(`/indicators/${code}/map`, { lang: locale, year: by }) : null;
        if (!off) setData({ now, base });
      } catch (e) { if (!off) setErr((e as Error).message); }
    })();
    return () => { off = true; };
  }, [code, locale]);

  const scenes = useMemo<Scene[]>(() => {
    if (!data) return [];
    const { now, base } = data;
    const ind = now.indicator;
    const rows = now.data.filter((r) => r.iso_numeric);
    if (rows.length < 10) return [];
    const sign = ind.higher_is_worse ? 1 : -1;               // sign * value is larger when it is worse
    const unit = label("units", ind.unit);
    const f = (v: number) => num(v, Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2);
    const yr = num(now.year, 0).replace(/[,٬]/g, "");
    const out: Scene[] = [];
    const vals = rows.map((r) => r.value);
    out.push({
      id: "world", target: null, mark: [],
      title: fa ? `جهان در ${yr}` : `The world in ${yr}`,
      text: fa
        ? `برای «${ind.name}» در ${yr}، ${num(rows.length, 0)} کشور از ${num(now.n_total, 0)} کشور مقدار دارند. مقدارها از ${f(Math.min(...vals))} تا ${f(Math.max(...vals))} (${unit}) است و کشورِ میانه ${f(median(vals))} دارد.`
        : `For “${ind.name}” in ${yr}, ${num(rows.length, 0)} of ${num(now.n_total, 0)} countries have a value. Values run from ${f(Math.min(...vals))} to ${f(Math.max(...vals))} (${unit}); the median country is ${f(median(vals))}.`,
    });
    const groups = new Map<string, MapRow[]>();
    for (const r of rows) if (r.region) (groups.get(r.region) ?? groups.set(r.region, []).get(r.region)!).push(r);
    const regs = [...groups.entries()].filter(([, v]) => v.length >= 5).map(([k, v]) => ({ k, v, med: median(v.map((r) => r.value)) }));
    if (regs.length >= 2) {
      const worst = regs.reduce((a, b) => (sign * b.med > sign * a.med ? b : a));
      out.push({
        id: "region", target: worst.v.map((r) => r.iso_numeric!), mark: worst.v.map((r) => r.iso_numeric!), dimOthers: true,
        title: worst.k,
        text: fa
          ? `بین مناطق (دسته‌بندی بانک جهانی)، ${worst.k} ${ind.higher_is_worse ? "بالاترین" : "پایین‌ترین"} میانه را دارد: ${f(worst.med)} ${unit}، بر پایه‌ی ${num(worst.v.length, 0)} کشور. میانه‌ی کشورها، نه میانگین جمعیت‌وزنی.`
          : `Among World Bank regions, ${worst.k} has the ${ind.higher_is_worse ? "highest" : "lowest"} median: ${f(worst.med)} ${unit}, from ${num(worst.v.length, 0)} countries. This is the median of countries, not a population-weighted average.`,
      });
    }
    const w = rows.reduce((a, b) => (sign * b.value > sign * a.value ? b : a));
    const ci = w.low != null && w.high != null ? (fa ? ` (بازه‌ی ${f(w.low)} تا ${f(w.high)})` : ` (range ${f(w.low)} to ${f(w.high)})`) : "";
    out.push({
      id: "worst", target: [w.iso_numeric!], mark: [w.iso_numeric!],
      title: w.name,
      text: fa
        ? `${ind.higher_is_worse ? "بدترین" : "پایین‌ترین"} مقدار گزارش‌شده در ${yr}: ${w.name} با ${f(w.value)} ${unit}${ci}. این برآورد منبع است و ممکن است عدم‌قطعیت زیادی داشته باشد.`
        : `The ${ind.higher_is_worse ? "worst" : "lowest"} reported value in ${yr}: ${w.name} at ${f(w.value)} ${unit}${ci}. This is the source's estimate and may carry wide uncertainty.`,
    });
    if (base) {
      const bmap = new Map(base.data.map((r) => [r.iso3, r.value]));
      const bmed = median([...bmap.values()]);
      const cand = rows.filter((r) => bmap.has(r.iso3) && (bmap.get(r.iso3) as number) > 0 && (bmap.get(r.iso3) as number) >= bmed)
        .map((r) => { const b = bmap.get(r.iso3) as number; return { r, b, gain: (sign * (b - r.value)) / b }; });
      if (cand.length) {
        const best = cand.reduce((a, b) => (b.gain > a.gain ? b : a));
        if (best.gain > 0) {
          const by = num(base.year, 0).replace(/[,٬]/g, "");
          out.push({
            id: "gain", target: [best.r.iso_numeric!], mark: [best.r.iso_numeric!],
            title: best.r.name,
            text: fa
              ? `از ${by} تا ${yr} در میان کشورهایی که در ${by} دست‌کم مقدار میانه را داشتند، ${best.r.name} بیشترین بهبود نسبی را نشان می‌دهد: از ${f(best.b)} به ${f(best.r.value)} ${unit}. این بهبود به‌تنهایی دلیل آن را نشان نمی‌دهد.`
              : `From ${by} to ${yr}, among countries that started at or above the median, ${best.r.name} shows the largest relative improvement: ${f(best.b)} to ${f(best.r.value)} ${unit}. The numbers alone do not explain why.`,
          });
        }
      }
    }
    out.push({
      id: "caveat", target: null, mark: [],
      title: fa ? "آنچه این نقشه نشان نمی‌دهد" : "What this map does not show",
      text: T.storyDisclaimer,
    });
    return out;
  }, [data, label, num, fa, T.storyDisclaimer]);

  const scene = scenes[Math.min(i, Math.max(0, scenes.length - 1))];

  useEffect(() => {
    if (!auto || !scenes.length) return;
    const id = window.setTimeout(() => setI((n) => (n + 1 < scenes.length ? n + 1 : 0)), 9000);
    return () => window.clearTimeout(id);
  }, [auto, i, scenes.length]);

  const byId = useMemo(() => new Map(shapes.map((s) => [s.id, s])), [shapes]);
  const cam = useMemo(() => {
    const ids = scene?.target?.filter((x) => byId.has(x)) ?? [];
    if (!ids.length) return { k: 1, x: 0, y: 0 };
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const id of ids) { const b = byId.get(id)!.bbox; x0 = Math.min(x0, b[0][0]); y0 = Math.min(y0, b[0][1]); x1 = Math.max(x1, b[1][0]); y1 = Math.max(y1, b[1][1]); }
    const bw = x1 - x0, bh = y1 - y0;
    if (bw > 0.7 * W || bh > 0.9 * H) return { k: 1, x: 0, y: 0 };   // spans the whole map (or crosses the date line)
    const k = Math.max(1, Math.min(7, 0.7 * Math.min(W / bw, H / bh)));
    return { k, x: W / 2 - (k * (x0 + x1)) / 2, y: H / 2 - (k * (y0 + y1)) / 2 };
  }, [scene, byId]);

  const color = useMemo(() => {
    if (!data) return () => NO_DATA;
    const th = scaleThreshold<number, string>().domain(data.now.breaks.slice(1, -1)).range(data.now.indicator.higher_is_worse ? RAMP_BURDEN : RAMP_GOOD);
    const m = new Map(data.now.data.map((r) => [r.iso_numeric, r.value]));
    return (id: string) => { const v = m.get(id); return v == null ? NO_DATA : th(v); };
  }, [data]);

  const go = (d: number) => setI((n) => Math.min(scenes.length - 1, Math.max(0, n + d)));
  const onKey = (e: React.KeyboardEvent) => {
    const fwd = dir === "rtl" ? "ArrowLeft" : "ArrowRight", back = dir === "rtl" ? "ArrowRight" : "ArrowLeft";
    if (e.key === fwd) { e.preventDefault(); go(1); } else if (e.key === back) { e.preventDefault(); go(-1); }
  };

  if (opts.loading) return <p className="muted">{T.loading}</p>;
  const list = opts.data?.indicators ?? [];

  return (
    <section aria-label={T.tabs.story}>
      <div className="viz-controls">
        <label>{T.pickInd}
          <select value={code ?? ""} onChange={(e) => setCode(e.target.value)}>
            {list.map((o) => <option key={o.code} value={o.code}>{o.name}</option>)}
          </select>
        </label>
        <label className="viz-check"><input type="checkbox" checked={auto} disabled={reduced} onChange={(e) => setAuto(e.target.checked)} /> {T.auto}</label>
      </div>
      {err && <p className="notice">{err.startsWith("404") ? T.failed : err}</p>}
      {!data && !err && <p className="muted">{T.loading}</p>}
      {data && !scenes.length && <p className="notice">{T.failed}</p>}

      {data && scene && (
        <div className="viz-story" ref={root} tabIndex={0} onKeyDown={onKey} aria-label={`${T.tabs.story} — ${T.scene} ${num(i + 1, 0)} / ${num(scenes.length, 0)}`}>
          <div className="viz-stage viz-map" dir="ltr">
            <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${data.now.indicator.name}, ${data.now.year}`}>
              <g style={{ transform: `translate(${cam.x}px, ${cam.y}px) scale(${cam.k})`, transition: reduced ? "none" : "transform 1.4s cubic-bezier(.65,0,.35,1)" }}>
                {shapes.map((s, idx) => {
                  const marked = scene.mark.includes(s.id);
                  return <path key={s.id + "-" + idx} d={s.d} fill={color(s.id)} vectorEffect="non-scaling-stroke"
                    fillOpacity={scene.dimOthers && !marked ? 0.28 : 1}
                    stroke={marked ? "#fff" : "rgba(8,20,30,.5)"} strokeWidth={marked ? 2 : 0.5} />;
                })}
                {scene.mark.slice(0, 1).map((id) => {
                  const s = byId.get(id);
                  return s && scene.id !== "region" ? <text key={id} x={s.c[0]} y={s.c[1] - 8 / cam.k} textAnchor="middle" className="viz-label" style={{ fontSize: 13 / cam.k }}>{s.name}</text> : null;
                })}
              </g>
            </svg>
          </div>

          <article className="viz-narr" aria-live="polite" dir={dir}>
            <h3>{scene.title}</h3>
            <p>{scene.text}</p>
            <div className="viz-steps">
              <button type="button" onClick={() => go(-1)} disabled={i === 0}>{T.prev}</button>
              <span role="group" aria-label={T.scene}>
                {scenes.map((s, n) => (
                  <button type="button" key={s.id} className={"dot" + (n === i ? " on" : "")} aria-label={`${T.scene} ${num(n + 1, 0)}`} aria-current={n === i} onClick={() => setI(n)} />
                ))}
              </span>
              <button type="button" onClick={() => go(1)} disabled={i === scenes.length - 1}>{T.next}</button>
            </div>
          </article>
        </div>
      )}
      {data && (
        <p className="small muted">
          {T.source}: {data.now.indicator.source.name} ({data.now.indicator.source.license ?? "—"}). {T.corr}{" "}
          <Link href={`/${locale}/explore`}>{fa ? "کاوش کامل" : "Open the explorer"}</Link>
        </p>
      )}
    </section>
  );
}
