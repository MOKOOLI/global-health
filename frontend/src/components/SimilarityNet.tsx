"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type Simulation, type SimulationLinkDatum, type SimulationNodeDatum } from "d3-force";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { VIZ_TXT, clusterColor, type SimNode, type SimResp } from "@/lib/viz";

const W = 960, H = 640;
type N = SimNode & SimulationNodeDatum & { r: number };
type L = SimulationLinkDatum<N> & { w: number };

export default function SimilarityNet() {
  const { locale, num } = useLocale();
  const T = VIZ_TXT[locale];
  const res = useApi<SimResp>("/viz/similarity", { lang: locale, k: 4 });
  const d = res.data;

  const [, setTick] = useState(0);
  const nodes = useRef<N[]>([]);
  const links = useRef<L[]>([]);
  const sim = useRef<Simulation<N, L> | null>(null);
  const svg = useRef<SVGSVGElement | null>(null);
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  const viewRef = useRef(view);
  viewRef.current = view;
  const touched = useRef(false);
  const [sel, setSel] = useState<string | null>(null);
  const [focusCluster, setFocusCluster] = useState<number | null>(null);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const m = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(m.matches);
  }, []);

  // build and run the force layout whenever the data arrive
  useEffect(() => {
    if (!d) return;
    const maxPop = Math.max(1, ...d.nodes.map((n) => n.population ?? 0));
    const nc = Math.max(1, d.clusters.length);
    const ns: N[] = d.nodes.map((n, i) => {
      const a = (n.cluster / nc) * Math.PI * 2;
      return { ...n, r: 3 + 8 * Math.sqrt((n.population ?? 0) / maxPop), x: W / 2 + Math.cos(a) * 200 + (i % 7), y: H / 2 + Math.sin(a) * 200 + (i % 5) };
    });
    const ids = new Map(ns.map((n) => [n.iso3, n]));
    const ls: L[] = d.edges.filter((e) => ids.has(e.s) && ids.has(e.t)).map((e) => ({ source: e.s, target: e.t, w: e.w }));
    nodes.current = ns; links.current = ls;
    const center = (c: number) => {
      const a = (c / nc) * Math.PI * 2;
      return [W / 2 + Math.cos(a) * 190, H / 2 + Math.sin(a) * 150] as const;
    };
    const s = forceSimulation<N>(ns)
      .force("link", forceLink<N, L>(ls).id((n) => n.iso3).distance((l) => 18 + (1 - l.w) * 160).strength(0.35))
      .force("charge", forceManyBody<N>().strength(-34))
      .force("collide", forceCollide<N>().radius((n) => n.r + 1.5))
      .force("gx", forceX<N>((n) => center(n.cluster)[0]).strength(0.07))
      .force("gy", forceY<N>((n) => center(n.cluster)[1]).strength(0.09))
      .stop();
    sim.current = s;
    if (reduced) {
      for (let i = 0; i < 320; i++) s.tick();        // settle off-screen, show the result without motion
      setTick((v) => v + 1);
    } else {
      s.on("tick", () => setTick((v) => v + 1)).alpha(1).restart();
    }
    touched.current = false;
    const fit = () => {
      if (touched.current) return;
      const xs = ns.map((n) => n.x ?? 0), ys = ns.map((n) => n.y ?? 0);
      const x0 = Math.min(...xs) - 20, x1 = Math.max(...xs) + 20, y0 = Math.min(...ys) - 20, y1 = Math.max(...ys) + 20;
      const k = Math.min(3, Math.max(0.6, 0.94 * Math.min(W / (x1 - x0), H / (y1 - y0))));
      setView({ k, x: W / 2 - (k * (x0 + x1)) / 2, y: H / 2 - (k * (y0 + y1)) / 2 });
    };
    const timer = window.setTimeout(fit, reduced ? 0 : 2400);
    return () => { s.stop(); window.clearTimeout(timer); };
  }, [d, reduced]);

  // wheel zoom needs a non-passive listener
  useEffect(() => {
    const el = svg.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W, py = ((e.clientY - r.top) / r.height) * H;
      zoomAt(px, py, e.deltaY < 0 ? 1.15 : 1 / 1.15);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [d]); // eslint-disable-line react-hooks/exhaustive-deps

  function zoomAt(px: number, py: number, f: number) {
    touched.current = true;
    const v = viewRef.current;
    const k = Math.min(8, Math.max(0.6, v.k * f));
    const g = k / v.k;
    setView({ k, x: px - (px - v.x) * g, y: py - (py - v.y) * g });
  }

  const toGraph = (clientX: number, clientY: number) => {
    const r = svg.current!.getBoundingClientRect();
    const v = viewRef.current;
    return [(((clientX - r.left) / r.width) * W - v.x) / v.k, (((clientY - r.top) / r.height) * H - v.y) / v.k] as const;
  };

  // pan (background) and drag (node) with pointer events
  const drag = useRef<{ kind: "pan" | "node"; node?: N; sx: number; sy: number; vx: number; vy: number; moved: boolean } | null>(null);
  const onDown = (e: React.PointerEvent, node?: N) => {
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    drag.current = { kind: node ? "node" : "pan", node, sx: e.clientX, sy: e.clientY, vx: viewRef.current.x, vy: viewRef.current.y, moved: false };
    if (node) { e.stopPropagation(); node.fx = node.x; node.fy = node.y; sim.current?.alphaTarget(0.25).restart(); }
  };
  const onMove = (e: React.PointerEvent) => {
    const s = drag.current;
    if (!s) return;
    if (Math.abs(e.clientX - s.sx) + Math.abs(e.clientY - s.sy) > 3) { s.moved = true; touched.current = true; }
    if (s.kind === "pan") {
      const r = svg.current!.getBoundingClientRect();
      setView((v) => ({ ...v, x: s.vx + ((e.clientX - s.sx) / r.width) * W, y: s.vy + ((e.clientY - s.sy) / r.height) * H }));
    } else if (s.node) {
      const [gx, gy] = toGraph(e.clientX, e.clientY);
      s.node.fx = gx; s.node.fy = gy;
      if (reduced) setTick((v) => v + 1);
    }
  };
  const onUp = () => {
    const s = drag.current;
    drag.current = null;
    if (s?.node) {
      s.node.fx = null; s.node.fy = null;
      sim.current?.alphaTarget(0);
      if (!s.moved) setSel((c) => (c === s.node!.iso3 ? null : s.node!.iso3));
    }
  };

  const byIso = useMemo(() => new Map((d?.nodes ?? []).map((n) => [n.iso3, n])), [d]);
  const neighbours = useMemo(() => {
    const m = new Map<string, { iso3: string; w: number }[]>();
    for (const e of d?.edges ?? []) {
      (m.get(e.s) ?? m.set(e.s, []).get(e.s)!).push({ iso3: e.t, w: e.w });
      (m.get(e.t) ?? m.set(e.t, []).get(e.t)!).push({ iso3: e.s, w: e.w });
    }
    return m;
  }, [d]);
  const selNb = useMemo(() => new Set((sel ? neighbours.get(sel) ?? [] : []).map((n) => n.iso3)), [sel, neighbours]);

  if (res.loading) return <p className="muted">{T.loading}</p>;
  if (res.error || !d) return <p className="notice">{res.error?.startsWith("404") ? res.error.replace(/^404: /, "") : T.failed}</p>;

  const dim = (n: N) => (focusCluster !== null && n.cluster !== focusCluster) || (sel !== null && n.iso3 !== sel && !selNb.has(n.iso3));
  const selNode = sel ? byIso.get(sel) : null;
  const selCluster = selNode ? d.clusters.find((c) => c.id === selNode.cluster) : null;
  const featText = (c: SimResp["clusters"][number]) =>
    c.features.map((f) => `${f.direction === "high" ? T.higher : T.lower}: ${f.name}`).join(" · ");

  return (
    <section aria-label={T.tabs.network}>
      <p>{T.netLead}</p>
      <p className="warn-box">{T.netCaveat}</p>

      <div className="viz-controls">
        <label>{T.highlight}
          <select value={sel ?? ""} onChange={(e) => setSel(e.target.value || null)}>
            <option value="">{T.none}</option>
            {[...d.nodes].sort((a, b) => a.name.localeCompare(b.name, locale)).map((n) => <option key={n.iso3} value={n.iso3}>{n.name}</option>)}
          </select>
        </label>
        <span className="viz-chips">
          <button type="button" onClick={() => zoomAt(W / 2, H / 2, 1.3)}>{T.zoomIn} +</button>
          <button type="button" onClick={() => zoomAt(W / 2, H / 2, 1 / 1.3)}>{T.zoomOut} −</button>
          <button type="button" onClick={() => { touched.current = false; setView({ k: 1, x: 0, y: 0 }); setSel(null); setFocusCluster(null); }}>{T.reset}</button>
        </span>
        <span className="muted small">{T.dragHint}</span>
      </div>

      <div className="viz-stage" dir="ltr">
        <svg ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={T.tabs.network} className="viz-net"
          onPointerDown={(e) => onDown(e)} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
          <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
            {links.current.map((l, i) => {
              const a = l.source as N, b = l.target as N;
              if (a.x == null || b.x == null) return null;
              const hot = sel !== null && (a.iso3 === sel || b.iso3 === sel);
              const faded = (sel !== null && !hot) || (focusCluster !== null && (a.cluster !== focusCluster || b.cluster !== focusCluster));
              return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={hot ? "#fff" : "#7F95A8"}
                strokeOpacity={faded ? 0.04 : hot ? 0.85 : 0.1 + 0.3 * l.w} strokeWidth={(hot ? 1.6 : 0.8) / view.k} />;
            })}
            {nodes.current.map((n) => (
              <circle key={n.iso3} cx={n.x} cy={n.y} r={n.r} fill={clusterColor(n.cluster)} fillOpacity={dim(n) ? 0.15 : 0.92}
                stroke={n.iso3 === sel ? "#fff" : "rgba(8,20,30,.6)"} strokeWidth={(n.iso3 === sel ? 2.5 : 0.8) / view.k}
                onPointerDown={(e) => onDown(e, n)} style={{ cursor: "grab" }}>
                <title>{n.name}</title>
              </circle>
            ))}
            {(sel ? [sel, ...selNb] : []).map((iso) => {
              const n = nodes.current.find((q) => q.iso3 === iso);
              return n && n.x != null ? <text key={"t" + iso} x={n.x + n.r + 3} y={n.y! + 3} className="viz-label" style={{ fontSize: 11 / view.k }}>{byIso.get(iso)?.name}</text> : null;
            })}
          </g>
        </svg>
      </div>

      {selNode && (
        <div className="viz-card" role="status">
          <h3>{selNode.name}</h3>
          <p className="small">{T.similarTo}:{" "}
            {(neighbours.get(selNode.iso3) ?? []).sort((a, b) => b.w - a.w).slice(0, 5).map((nb, i) => (
              <span key={nb.iso3}>{i ? ", " : ""}<button type="button" className="linklike" onClick={() => setSel(nb.iso3)}>{byIso.get(nb.iso3)?.name}</button></span>
            ))}
          </p>
          {selCluster && <p className="small muted">{featText(selCluster)}</p>}
          <p className="small"><Link href={`/${locale}/country/${selNode.iso3}`}>{T.openCountry}</Link></p>
        </div>
      )}

      <h2>{T.groups}</h2>
      <div className="viz-groups">
        {d.clusters.slice(0, 8).map((c) => (
          <div key={c.id} className={"viz-group" + (focusCluster === c.id ? " on" : "")}>
            <button type="button" aria-pressed={focusCluster === c.id} onClick={() => setFocusCluster((f) => (f === c.id ? null : c.id))}>
              <i style={{ background: clusterColor(c.id) }} /> {num(c.size, 0)} {T.members}
            </button>
            <p className="small">{featText(c) || "—"}</p>
            <p className="small muted">{T.examples}: {c.examples.join(locale === "fa" ? "، " : ", ")}</p>
            <details>
              <summary className="small">{T.members}</summary>
              <ul className="small viz-members">
                {d.nodes.filter((n) => n.cluster === c.id).sort((a, b) => a.name.localeCompare(b.name, locale)).map((n) => (
                  <li key={n.iso3}><Link href={`/${locale}/country/${n.iso3}`}>{n.name}</Link></li>
                ))}
              </ul>
            </details>
          </div>
        ))}
        {d.clusters.length > 8 && (
          <div className="viz-group">
            <p className="small"><i style={{ background: clusterColor(99) }} /> {num(d.clusters.slice(8).reduce((a, c) => a + c.size, 0), 0)} {T.members}</p>
            <p className="small muted">{T.otherGroups.replace("{n}", String(d.clusters.length - 8))}</p>
          </div>
        )}
      </div>

      <details>
        <summary>{T.netHow}</summary>
        <p className="small">{d.method}</p>
        <p className="small muted">{T.indicatorsUsed}: {d.indicators.map((i) => i.name).join(" · ")}</p>
      </details>
    </section>
  );
}
