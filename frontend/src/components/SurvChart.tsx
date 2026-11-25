"use client";

import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import type { LineSeriesOption } from "echarts/charts";
import { useEffect, useRef } from "react";
import type { Forecast, SeriesPoint } from "@/lib/surv";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, SVGRenderer]);

interface Props {
  points: SeriesPoint[]; upto: string; forecast: Forecast | null;
  labels: { observed: string; expected: string; upper: string; forecast: string };
  height?: number;
}

export default function SurvChart({ points, upto, forecast, labels, height = 300 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "svg" });
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    const shown = points.filter((p) => p.week_start <= upto).slice(-104); // last two years
    const fc = forecast?.points ?? [];
    const x = [...shown.map((p) => p.week_start), ...fc.map((p) => p.week_start)];
    const pad = fc.length;
    const nulls = Array(pad).fill(null);
    const s: LineSeriesOption[] = [
      { name: labels.upper, type: "line", showSymbol: false, data: [...shown.map((p) => p.upper), ...nulls],
        lineStyle: { width: 1, type: "dotted", color: "#8A4B00" }, itemStyle: { color: "#8A4B00" } },
      { name: labels.expected, type: "line", showSymbol: false, data: [...shown.map((p) => p.expected), ...nulls],
        lineStyle: { width: 1.5, color: "#6E9BC4" }, itemStyle: { color: "#6E9BC4" } },
      { name: labels.observed, type: "line", showSymbol: false, connectNulls: false,
        data: [...shown.map((p) => p.value), ...nulls], lineStyle: { width: 2.2, color: "#11202E" }, itemStyle: { color: "#11202E" } },
    ];
    if (fc.length) {
      const lastI = shown.length - 1;
      const band = (k: "low" | "high") => [...Array(lastI).fill(null), shown[lastI]?.value ?? null, ...fc.map((p) => p[k])];
      s.push({ name: labels.forecast, type: "line", showSymbol: false,
        data: [...Array(lastI).fill(null), shown[lastI]?.value ?? null, ...fc.map((p) => p.value)],
        lineStyle: { width: 2, type: "dashed", color: "#5B6B78" }, itemStyle: { color: "#5B6B78" } });
      s.push({ name: `${labels.forecast} 80%-`, type: "line", showSymbol: false, data: band("low"),
        lineStyle: { width: 0.8, type: "dashed", color: "#9AA7B1" }, itemStyle: { color: "#9AA7B1" }, tooltip: { show: false } });
      s.push({ name: `${labels.forecast} 80%+`, type: "line", showSymbol: false, data: band("high"),
        lineStyle: { width: 0.8, type: "dashed", color: "#9AA7B1" }, itemStyle: { color: "#9AA7B1" }, tooltip: { show: false } });
    }
    chart.setOption({
      animation: false, textStyle: { fontFamily: "inherit" },
      grid: { left: 8, right: 12, top: 34, bottom: 8, containLabel: true },
      tooltip: { trigger: "axis", confine: true },
      legend: { top: 0, data: [labels.observed, labels.expected, labels.upper, ...(fc.length ? [labels.forecast] : [])] },
      xAxis: { type: "category", data: x, boundaryGap: false, axisLabel: { hideOverlap: true } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: "#E3E8EC" } } },
      series: s,
    });
    return () => { ro.disconnect(); chart.dispose(); };
  }, [points, upto, forecast, labels]);
  return <div ref={ref} style={{ width: "100%", height }} role="img" aria-label={labels.observed} />;
}
