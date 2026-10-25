"use client";
import { useEffect, useRef } from "react";
import { ColorType, createChart } from "lightweight-charts";
import type { Candle } from "@/lib/api";
import { chartColors, useTheme } from "@/lib/theme";

function sma(c: Candle[], n: number) {
  const out: { time: string; value: number }[] = [];
  let s = 0;
  c.forEach((x, i) => {
    s += x.close;
    if (i >= n) s -= c[i - n].close;
    if (i >= n - 1) out.push({ time: x.date, value: s / n });
  });
  return out;
}

export default function Chart({ candles, sma20, sma50 }: { candles: Candle[]; sma20: boolean; sma50: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const theme = useTheme();
  useEffect(() => {
    if (!ref.current || candles.length === 0) return;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: chartColors(theme).text },
      grid: { vertLines: { color: chartColors(theme).grid }, horzLines: { color: chartColors(theme).grid } },
      rightPriceScale: { borderColor: chartColors(theme).grid }, timeScale: { borderColor: chartColors(theme).grid },
    });
    const cs = chart.addCandlestickSeries({
      upColor: "#22c55e", downColor: "#ef4444", wickUpColor: "#22c55e", wickDownColor: "#ef4444", borderVisible: false,
    });
    cs.setData(candles.map((c) => ({ time: c.date, open: c.open, high: c.high, low: c.low, close: c.close })));
    if (candles.some((c) => c.volume != null)) {
      const v = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "" });
      v.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      v.setData(candles.map((c) => ({ time: c.date, value: c.volume ?? 0,
        color: c.close >= c.open ? "#22c55e55" : "#ef444455" })));
    }
    if (sma20) chart.addLineSeries({ color: "#60a5fa", lineWidth: 1, priceLineVisible: false }).setData(sma(candles, 20));
    if (sma50) chart.addLineSeries({ color: "#f59e0b", lineWidth: 1, priceLineVisible: false }).setData(sma(candles, 50));
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candles, sma20, sma50, theme]);
  return <div ref={ref} className="h-full w-full" />;
}
