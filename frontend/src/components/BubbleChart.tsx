"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { scaleLinear, scaleLog, scaleSqrt } from "d3-scale";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { VIZ_TXT, regionColor, regionName, type BubbleCountry, type BubblesResp, type VizOptions } from "@/lib/viz";

const W = 960, H = 540, M = { l: 70, r: 24, t: 24, b: 56 };

/** Linear interpolation of a country's point at fractional year t; null outside its measured span. */
function at(c: BubbleCountry, t: number, smooth: boolean): [number, number, number] | null {
  const p = c.points;
  if (!p.length || t < p[0][0] || t > p[p.length - 1][0]) return null;
  let i = 0;
  while (i < p.length - 1 && p[i + 1][0] <= t) i++;
  const a = p[i], b = p[Math.min(i + 1, p.length - 1)];
  if (!smooth || a === b || t <= a[0]) return [a[0], a[1], a[2]];
  const f = (t - a[0]) / (b[0] - a[0]);
  return [t, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

export default function BubbleChart() {
  const { locale, num, dir } = useLocale();
  const T = VIZ_TXT[locale];
  const opts = useApi<VizOptions>("/viz/options", { lang: locale });
  const [x, setX] = useState<string | null>(null);
  const [y, setY] = useState<string | null>(null);
  useEffect(() => {
    if (opts.data?.default && !x && !y) { setX(opts.data.default.x); setY(opts.data.default.y); }
  }, [opts.data, x, y]);
  const res = useApi<BubblesResp>(x && y && x !== y ? "/viz/bubbles" : null, { x, y, lang: locale });
  const d = res.data;

  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [logOn, setLogOn] = useState(true);
  const [pinned, setPinned] = useState<string[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hover, setHover] = useState<{ c: BubbleCountry; px: number; py: number } | null>(null);
  const [reduced, setReduced] = useState(false);
  const raf = useRef(0);
  const tRef = useRef(0);

  useEffect(() => {
    const m = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(m.matches);
    const f = () => setReduced(m.matches);
    m.addEventListener("change", f);
    return () => m.removeEventListener("change", f);
  }, []);

  const y0 = d?.years[0] ?? 0, y1 = d ? d.years[d.years.length - 1] : 0;
  useEffect(() => { if (d) { setT(d.years[d.years.length - 1]); tRef.current = d.years[d.years.length - 1]; setPlaying(false); setPinned([]); } }, [d]);

  // animation loop (continuous), or one step per second when the person prefers reduced motion
  useEffect(() => {
    if (!playing || !d) return;
    if (reduced) {
      const id = window.setInterval(() => {
        const next = Math.round(tRef.current) + 1;
        if (next > y1) { setPlaying(false); return; }
        tRef.current = next; setT(next);
      }, 1000 / speed);
      return () => window.clearInterval(id);
    }
    let last = performance.now();
    const tick = (now: number) => {
      const dt = (now - last) / 1000; last = now;
      const next = Math.min(y1, tRef.current + dt * 2 * speed);
      tRef.current = next; setT(next);
      if (next >= y1) { setPlaying(false); return; }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, d, reduced, speed, y1]);

  const togglePlay = useCallback(() => {
    if (!d) return;
    if (!playing && tRef.current >= y1) { tRef.current = y0; setT(y0); }
    setPlaying((p) => !p);
  }, [d, playing, y0, y1]);

  const canLog = !!d && d.x_range[0] > 0;
  const useLog = logOn && canLog;
  const sx = useMemo(() => {
    if (!d) return null;
    const [a, b] = d.x_range;
    return (useLog ? scaleLog().domain([a * 0.9, b * 1.1]).nice() : scaleLinear().domain([Math.min(0, a), b * 1.05]).nice()).range([M.l, W - M.r]);
  }, [d, useLog]);
  const sy = useMemo(() => {
    if (!d) return null;
    const [a, b] = d.y_range;
    return scaleLinear().domain([Math.min(0, a), b * 1.05]).nice().range([H - M.b, M.t]);
  }, [d]);
  const sr = useMemo(() => {
    const pops = (d?.countries ?? []).map((c) => c.population ?? 0).filter((p) => p > 0);
    return scaleSqrt().domain([0, Math.max(1, ...pops)]).range([3, 30]);
  }, [d]);

  const regions = useMemo(() => Array.from(new Set((d?.countries ?? []).map((c) => c.region ?? "—"))).sort(), [d]);
  const smooth = !reduced;
  const frame = useMemo(() => {
    if (!d || !sx || !sy) return [];
    return d.countries
      .filter((c) => !hidden.has(c.region ?? "—"))
      .map((c) => ({ c, p: at(c, t, smooth) }))
      .filter((r): r is { c: BubbleCountry; p: [number, number, number] } => r.p !== null)
      .sort((a, b) => (b.c.population ?? 0) - (a.c.population ?? 0)); // big bubbles behind small ones
  }, [d, sx, sy, t, smooth, hidden]);

  const yearNow = Math.round(t);
  const optList = opts.data?.indicators ?? [];
  const fmtTick = (v: number) => num(v, v >= 100 ? 0 : v >= 1 ? 1 : 2);
  const ticks = (s: { ticks: (n: number) => number[] } | null, n: number, thin = false) => {
    const t = s ? s.ticks(n) : [];
    // log axes: keep only 1, 2 and 5 times a power of ten, otherwise the labels collide
    return thin ? t.filter((v) => [1, 2, 5].includes(Number((v / 10 ** Math.floor(Math.log10(v))).toFixed(0)))) : t;
  };

  if (opts.loading) return <p className="muted">{T.loading}</p>;
  if (opts.error || !optList.length) return <p className="notice">{T.failed}</p>;

  return (
    <section aria-label={T.tabs.bubbles}>
      <div className="viz-controls">
        <label>{T.xAxis}
          <select value={x ?? ""} onChange={(e) => setX(e.target.value)}>
            {optList.map((o) => <option key={o.code} value={o.code}>{o.name}</option>)}
          </select>
        </label>
        <label>{T.yAxis}
          <select value={y ?? ""} onChange={(e) => setY(e.target.value)}>
            {optList.map((o) => <option key={o.code} value={o.code}>{o.name}</option>)}
          </select>
        </label>
        {canLog && <label className="viz-check"><input type="checkbox" checked={logOn} onChange={(e) => setLogOn(e.target.checked)} /> {T.log}</label>}
      </div>

      {x === y && <p className="notice">{T.tooFew}</p>}
      {res.loading && <p className="muted">{T.loading}</p>}
      {res.error && <p className="notice">{res.error.startsWith("404") ? T.tooFew : T.failed}</p>}

      {d && sx && sy && (
        <>
          <div className="viz-stage" dir="ltr">
            <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${d.x.name} / ${d.y.name}, ${yearNow}`} onMouseLeave={() => setHover(null)}>
              <text className="viz-year" x={W - M.r - 8} y={H - M.b - 18} textAnchor="end">{num(yearNow, 0).replace(/[,٬]/g, "")}</text>
              {ticks(sy, 6).map((v) => (
                <g key={"y" + v}>
                  <line x1={M.l} x2={W - M.r} y1={sy(v)} y2={sy(v)} className="viz-grid" />
                  <text x={M.l - 8} y={sy(v)} dy="0.32em" textAnchor="end" className="viz-tick">{fmtTick(v)}</text>
                </g>
              ))}
              {ticks(sx as never, useLog ? 6 : 8, useLog).map((v) => (
                <g key={"x" + v}>
                  <line y1={M.t} y2={H - M.b} x1={sx(v)} x2={sx(v)} className="viz-grid" />
                  <text y={H - M.b + 18} x={sx(v)} textAnchor="middle" className="viz-tick">{fmtTick(v)}</text>
                </g>
              ))}
              <text x={(M.l + W - M.r) / 2} y={H - 10} textAnchor="middle" className="viz-axis">
                {d.x.name}{d.x.higher_is_worse ? ` (${T.worse} →)` : ` (← ${T.worse})`}
              </text>
              <text transform={`translate(16 ${(M.t + H - M.b) / 2}) rotate(-90)`} textAnchor="middle" className="viz-axis">
                {d.y.name}{d.y.higher_is_worse ? ` (${T.worse} →)` : ` (← ${T.worse})`}
              </text>

              {pinned.map((iso) => {
                const c = d.countries.find((k) => k.iso3 === iso);
                if (!c) return null;
                const pts = c.points.filter((p) => p[0] <= t).map((p) => `${sx(p[1])},${sy(p[2])}`).join(" ");
                return <polyline key={"tr" + iso} points={pts} fill="none" stroke={regionColor(c.region)} strokeWidth={1.5} strokeOpacity={0.7} strokeDasharray="4 3" />;
              })}

              {frame.map(({ c, p }) => {
                const isPin = pinned.includes(c.iso3);
                return (
                  <circle key={c.iso3} cx={sx(p[1])} cy={sy(p[2])} r={c.population ? sr(c.population) : 4}
                    fill={regionColor(c.region)} fillOpacity={isPin ? 0.95 : 0.62}
                    stroke={isPin ? "#fff" : "rgba(8,20,30,.55)"} strokeWidth={isPin ? 2 : 0.8}
                    onMouseEnter={(e) => setHover({ c, px: e.clientX, py: e.clientY })}
                    onMouseMove={(e) => setHover({ c, px: e.clientX, py: e.clientY })}
                    onClick={() => setPinned((s) => (s.includes(c.iso3) ? s.filter((i) => i !== c.iso3) : [...s, c.iso3].slice(-6)))} />
                );
              })}
              {pinned.map((iso) => {
                const f = frame.find((r) => r.c.iso3 === iso);
                if (!f) return null;
                return <text key={"lb" + iso} x={sx(f.p[1]) + 8} y={sy(f.p[2]) - 8} className="viz-label">{f.c.name}</text>;
              })}
            </svg>
            {hover && (
              <div className="viz-tip" style={{ left: hover.px + 14, top: hover.py + 14 }} role="status">
                <strong>{hover.c.name}</strong><br />
                {(() => { const p = at(hover.c, t, smooth); return p ? <>{d.x.name}: {fmtTick(p[1])}<br />{d.y.name}: {fmtTick(p[2])}<br />{T.year}: {num(Math.round(p[0]), 0).replace(/[,٬]/g, "")}</> : null; })()}
              </div>
            )}
          </div>

          <div className="viz-transport">
            <button type="button" className="btn-solid" onClick={togglePlay} aria-pressed={playing}>{playing ? T.pause : T.play}</button>
            <input type="range" min={y0} max={y1} step={1} value={yearNow} aria-label={T.year}
              onChange={(e) => { setPlaying(false); const v = Number(e.target.value); tRef.current = v; setT(v); }} />
            <label className="viz-check">{T.speed}
              <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                <option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option>
              </select>
            </label>
            <span className="muted small">{num(frame.length, 0)} {T.countriesNow}</span>
          </div>

          <div className="viz-legend" role="group" aria-label={T.regions}>
            {regions.map((r) => (
              <button type="button" key={r} className={hidden.has(r) ? "off" : ""} aria-pressed={!hidden.has(r)}
                onClick={() => setHidden((s) => { const n = new Set(s); if (n.has(r)) n.delete(r); else n.add(r); return n; })}>
                <i style={{ background: regionColor(r) }} />{regionName(r, locale)}
              </button>
            ))}
          </div>

          <div className="viz-controls">
            <label>{T.pin}
              <select value="" onChange={(e) => { const v = e.target.value; if (v) setPinned((s) => (s.includes(v) ? s : [...s, v].slice(-6))); }}>
                <option value="">{T.none}</option>
                {[...d.countries].sort((a, b) => a.name.localeCompare(b.name, locale)).map((c) => <option key={c.iso3} value={c.iso3}>{c.name}</option>)}
              </select>
            </label>
            {pinned.length > 0 && (
              <span className="viz-chips" aria-label={T.pinned}>
                {pinned.map((iso) => {
                  const c = d.countries.find((k) => k.iso3 === iso);
                  return <button type="button" key={iso} onClick={() => setPinned((s) => s.filter((i) => i !== iso))}>{c?.name ?? iso} ×</button>;
                })}
                <button type="button" onClick={() => setPinned([])}>{T.clear}</button>
              </span>
            )}
          </div>

          <p className="small muted">
            {T.sizeNote}{d.population_year ? ` (${num(d.population_year, 0).replace(/[,٬]/g, "")})` : ""}. {T.sizeYear}. {T.noPop}. {T.corr}
          </p>
          <p className="small muted">
            {T.source}: {d.x.source.name} ({d.x.source.license ?? "—"}){d.y.source.code !== d.x.source.code ? `; ${d.y.source.name} (${d.y.source.license ?? "—"})` : ""}
          </p>

          <details className="viz-table" dir={dir}>
            <summary>{T.table} ({num(yearNow, 0).replace(/[,٬]/g, "")})</summary>
            <table>
              <thead><tr><th>{T.country}</th><th>{d.x.name}</th><th>{d.y.name}</th></tr></thead>
              <tbody>
                {frame.slice().sort((a, b) => a.c.name.localeCompare(b.c.name, locale)).map(({ c, p }) => (
                  <tr key={c.iso3}><td>{c.name}</td><td>{fmtTick(p[1])}</td><td>{fmtTick(p[2])}</td></tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      )}
    </section>
  );
}
