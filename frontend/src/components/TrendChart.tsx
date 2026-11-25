"use client";

import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import type { LineSeriesOption } from "echarts/charts";
import type { GridComponentOption, LegendComponentOption, TooltipComponentOption } from "echarts/components";
import { useEffect, useRef } from "react";
import type { TrendSeries } from "@/lib/types";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, SVGRenderer]);

type Opt = echarts.ComposeOption<LineSeriesOption | GridComponentOption | TooltipComponentOption | LegendComponentOption>;

export const SERIES_COLORS = ["#9C2F6B", "#14676F", "#C2791B", "#3B5BA9", "#5E8C2A", "#6B4E9B"];

interface Props {
  series: TrendSeries[];
  unitLabel: string;
  forecastLabel: string;
  height?: number;
  fontFamily?: string;
}

export default function TrendChart({ series, unitLabel, forecastLabel, height = 280, fontFamily }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "svg" });
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);

    const single = series.length === 1;
    const fc = single ? series[0].forecast?.points ?? [] : [];
    const yearSet = new Set<number>();
    series.forEach((s) => s.points.forEach((p) => yearSet.add(p.year)));
    fc.forEach((p) => yearSet.add(p.year));
    const years = [...yearSet].sort((a, b) => a - b);
    const at = (s: TrendSeries, key: "value" | "low" | "high") =>
      years.map((y) => {
        const p = s.points.find((q) => q.year === y);
        const v = p ? p[key] : null;
        return v === undefined ? null : v;
      });

    const opts: Opt = {
      animation: false,
      textStyle: { fontFamily: fontFamily ?? "inherit" },
      grid: { left: 8, right: 12, top: series.length > 1 ? 36 : 16, bottom: 8, containLabel: true },
      tooltip: { trigger: "axis", confine: true },
      legend: series.length > 1 ? { top: 0, textStyle: { fontFamily: fontFamily ?? "inherit" } } : undefined,
      xAxis: { type: "category", data: years.map(String), boundaryGap: false, axisLine: { lineStyle: { color: "#A9B4BD" } } },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#E3E8EC" } },
      },
      series: [] as LineSeriesOption[],
    };
    const out = opts.series as LineSeriesOption[];

    series.forEach((s, i) => {
      const color = SERIES_COLORS[i % SERIES_COLORS.length];
      if (single && s.points.some((p) => p.low != null && p.high != null)) {
        const low = at(s, "low");
        const high = at(s, "high");
        out.push({
          name: "low", type: "line", data: low, stack: "ui", symbol: "none",
          lineStyle: { opacity: 0 }, tooltip: { show: false }, silent: true,
        });
        out.push({
          name: "ui", type: "line", symbol: "none", stack: "ui", silent: true, tooltip: { show: false },
          data: high.map((h, k) => (h != null && low[k] != null ? h - (low[k] as number) : null)),
          lineStyle: { opacity: 0 }, areaStyle: { color, opacity: 0.14 },
        });
      }
      out.push({
        name: s.name, type: "line", data: at(s, "value"), showSymbol: false, connectNulls: true,
        lineStyle: { width: 2.4, color }, itemStyle: { color },
      });
    });

    if (fc.length) {
      const last = series[0].points[series[0].points.length - 1];
      out.push({
        name: forecastLabel, type: "line", showSymbol: false, connectNulls: true,
        lineStyle: { width: 2, type: "dashed", color: "#5B6B78" }, itemStyle: { color: "#5B6B78" },
        data: years.map((y) => {
          if (last && y === last.year) return last.value;
          const f = fc.find((p) => p.year === y);
          return f ? f.value : null;
        }),
      });
    }
    chart.setOption(opts);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [series, unitLabel, forecastLabel, fontFamily]);

  return (
    <figure className="chart">
      <figcaption className="small muted">{unitLabel}</figcaption>
      <div ref={ref} style={{ width: "100%", height }} role="img" aria-label={series.map((s) => s.name).join(", ")} />
    </figure>
  );
}
