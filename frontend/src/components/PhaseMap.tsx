"use client";

import MapNote from "./MapNote";
import { useEffect, useMemo, useState } from "react";
import { loadGeo, type Geo } from "./WorldMap";
import { PHASE_COLOR, type StatusRow } from "@/lib/surv";

export default function PhaseMap({ rows, selected, onSelect, phaseLabel, ariaLabel }: {
  rows: StatusRow[]; selected: string | null; onSelect: (iso3: string) => void;
  phaseLabel: (r: StatusRow) => string; ariaLabel: string;
}) {
  const [geo, setGeo] = useState<Geo[]>([]);
  const [tip, setTip] = useState<{ t: string; s: string; x: number; y: number } | null>(null);
  useEffect(() => { loadGeo().then(setGeo).catch(() => setGeo([])); }, []);
  const by = useMemo(() => {
    const m = new Map<string, StatusRow>();
    for (const r of rows) if (r.iso_numeric) m.set(r.iso_numeric, r);
    return m;
  }, [rows]);
  return (
    <div className="map-wrap">
      <svg viewBox="0 0 960 500" role="img" aria-label={ariaLabel} className="map-svg">
        {geo.map((g) => {
          const r = by.get(g.id);
          return (
            <path key={g.id} d={g.d} fill={r ? PHASE_COLOR[r.stale ? "no_data" : r.phase] : "#DCE1E5"}
              className={`country${r ? " has-data" : ""}${r && r.iso3 === selected ? " is-selected" : ""}`}
              onClick={() => r && onSelect(r.iso3)}
              onMouseMove={(e) => {
                const b = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                setTip({ t: r?.name ?? g.name, s: r ? phaseLabel(r) : "–", x: e.clientX - b.left, y: e.clientY - b.top });
              }}
              onMouseLeave={() => setTip(null)} />
          );
        })}
      </svg>
      {tip && (
        <div className="map-tip" style={{ insetInlineStart: tip.x + 12, top: tip.y + 12 }}>
          <strong>{tip.t}</strong><span>{tip.s}</span>
        </div>
      )}
      <MapNote />
    </div>
  );
}
