"use client";

import MapNote from "./MapNote";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { scaleThreshold } from "d3-scale";
import { feature } from "topojson-client";
import { useEffect, useMemo, useState } from "react";
import type { MapRow } from "@/lib/types";

const W = 960;
const H = 500;

export const RAMP_BURDEN = ["#F4E4EA", "#E3B0C4", "#CB6A98", "#9C2F6B", "#55154A"];
export const RAMP_GOOD = ["#E2F0EF", "#B1D9D6", "#6DB5B2", "#2F8588", "#0F4A56"];
export const NO_DATA = "#DCE1E5";

export interface Geo {
  id: string;
  name: string;
  d: string;
}

let topoCache: Promise<Geo[]> | null = null;

export function loadGeo(): Promise<Geo[]> {
  if (!topoCache) {
    topoCache = fetch("/countries-110m.json")
      .then((r) => r.json())
      .then((topo) => {
        const fc = feature(topo, topo.objects.countries) as unknown as {
          features: { id?: string | number; properties: { name: string } }[];
        };
        const projection = geoNaturalEarth1().fitSize([W, H], { type: "Sphere" });
        const path = geoPath(projection);
        return fc.features
          .filter((f) => String(f.id) !== "010") // Antarctica
          .map((f) => ({
            id: String(f.id ?? "").padStart(3, "0"),
            name: f.properties.name,
            d: path(f as never) ?? "",
          }));
      });
  }
  return topoCache;
}

interface Props {
  rows: MapRow[];
  breaks: number[];
  ramp: string[];
  selected?: string | null;
  onSelect: (iso3: string) => void;
  format: (v: number) => string;
  unitLabel: string;
  noDataLabel: string;
  ariaLabel: string;
}

export default function WorldMap({
  rows, breaks, ramp, selected, onSelect, format, unitLabel, noDataLabel, ariaLabel,
}: Props) {
  const [geo, setGeo] = useState<Geo[]>([]);
  const [hover, setHover] = useState<{ name: string; value: number | null; x: number; y: number } | null>(null);

  useEffect(() => {
    loadGeo().then(setGeo).catch(() => setGeo([]));
  }, []);

  const byNumeric = useMemo(() => {
    const m = new Map<string, MapRow>();
    for (const r of rows) if (r.iso_numeric) m.set(r.iso_numeric, r);
    return m;
  }, [rows]);

  const color = useMemo(() => {
    const inner = breaks.slice(1, -1); // 4 thresholds -> 5 bins
    return scaleThreshold<number, string>().domain(inner).range(ramp);
  }, [breaks, ramp]);

  return (
    <div className="map-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} className="map-svg">
        {geo.map((g) => {
          const row = byNumeric.get(g.id);
          const isSel = !!row && row.iso3 === selected;
          return (
            <path
              key={g.id}
              d={g.d}
              fill={row ? color(row.value) : NO_DATA}
              className={`country${row ? " has-data" : ""}${isSel ? " is-selected" : ""}`}
              onClick={() => row && onSelect(row.iso3)}
              onMouseMove={(e) => {
                const box = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                setHover({ name: row?.name ?? g.name, value: row ? row.value : null, x: e.clientX - box.left, y: e.clientY - box.top });
              }}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
      </svg>
      {hover && (
        <div className="map-tip" style={{ insetInlineStart: hover.x + 12, top: hover.y + 12 }}>
          <strong>{hover.name}</strong>
          <span>{hover.value === null ? noDataLabel : `${format(hover.value)} ${unitLabel}`}</span>
        </div>
      )}
      <Legend breaks={breaks} ramp={ramp} format={format} noDataLabel={noDataLabel} />
      <MapNote />
    </div>
  );
}

function Legend({ breaks, ramp, format, noDataLabel }: {
  breaks: number[]; ramp: string[]; format: (v: number) => string; noDataLabel: string;
}) {
  return (
    <ul className="legend" aria-hidden="true">
      {ramp.map((c, i) => (
        <li key={i}>
          <i style={{ background: c }} />
          <span>
            {format(breaks[i] ?? 0)}–{format(breaks[i + 1] ?? 0)}
          </span>
        </li>
      ))}
      <li>
        <i style={{ background: NO_DATA }} />
        <span>{noDataLabel}</span>
      </li>
    </ul>
  );
}
