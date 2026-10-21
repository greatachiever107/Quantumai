"use client";
import { useEffect, useRef } from "react";
import { ColorType, createChart } from "lightweight-charts";
import { chartColors, useTheme } from "@/lib/theme";

export type Series = { name: string; color: string; data: { time: string; value: number }[] };

export default function LineChart({ series }: { series: Series[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const theme = useTheme();
  useEffect(() => {
    if (!ref.current || series.length === 0) return;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: chartColors(theme).text },
      grid: { vertLines: { color: chartColors(theme).grid }, horzLines: { color: chartColors(theme).grid } },
      rightPriceScale: { borderColor: chartColors(theme).grid }, timeScale: { borderColor: chartColors(theme).grid },
    });
    series.forEach((s) => chart.addLineSeries({ color: s.color, lineWidth: 2, title: s.name }).setData(s.data));
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [series, theme]);
  return <div ref={ref} className="h-[340px] w-full" />;
}
