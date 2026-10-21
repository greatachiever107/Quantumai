"use client";
import { useEffect, useMemo, useState } from "react";
import LineChart, { Series } from "@/components/LineChart";
import Shell from "@/components/Shell";
import { Row, get } from "@/lib/api";

type Resp = { data_mode: string; note?: string; results: Row[]; equity: Record<string, { time: string; value: number }[]> };
const COLORS: Record<string, string> = { equal_weight: "#94a3b8", inv_vol_naive: "#f59e0b", inv_vol_forecast: "#2563eb" };
const LABEL: Record<string, string> = { equal_weight: "Equal weight", inv_vol_naive: "Sized by recent vol", inv_vol_forecast: "Sized by forecast vol" };

export default function Backtesting() {
  const [d, setD] = useState<Resp | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { get<Resp>("/backtest/sizing").then(setD).catch((e) => setErr(e.message)); }, []);
  const series: Series[] = useMemo(() => Object.entries(d?.equity ?? {}).map(([k, v]) =>
    ({ name: LABEL[k] ?? k, color: COLORS[k] ?? "#fff", data: v })), [d]);
  const cols: [string, string][] = [["cagr_pct", "CAGR %"], ["volatility_pct", "Volatility %"], ["sharpe", "Sharpe"],
    ["max_drawdown_pct", "Max drawdown %"], ["worst_day_pct", "Worst day %"], ["avg_annual_turnover", "Turnover/yr"], ["growth_of_1", "Growth of $1"]];
  return (
    <Shell mode={d?.data_mode === "none" ? "" : "live"} asOf={null}>
      {err && <div className="card text-down">Cannot reach the API ({err}).</div>}
      <div className="card tone-brand">
        <div className="mb-1 text-lg font-semibold">Position sizing backtest</div>
        <div className="mb-3 text-sm text-mute">Does holding less of the riskier stocks (using volatility forecasts) improve results versus equal weights?</div>
        {d?.data_mode === "none" && <div className="text-sm text-mute">No results yet. Run position_sizing.py, then refresh.</div>}
        {series.length > 0 && <LineChart series={series} />}
        <div className="mt-2 flex gap-4 text-xs">{series.map((s) => <span key={s.name} style={{ color: s.color }}>&#9632; {s.name}</span>)}</div>
      </div>
      {d && d.results.length > 0 && (
        <div className="card overflow-x-auto tone-info">
          <table className="w-full text-sm"><thead><tr><th className="th">Strategy</th>{cols.map(([, h]) => <th key={h} className="th pr-3">{h}</th>)}</tr></thead>
            <tbody>{d.results.map((r) => (
              <tr key={String(r.strategy)} className="border-t border-line"><td className="py-2 font-medium">{LABEL[String(r.strategy)] ?? String(r.strategy)}</td>
                {cols.map(([k]) => <td key={k} className="pr-3">{r[k]}</td>)}</tr>))}</tbody></table>
          <div className="mt-3 text-xs text-mute">{d.note}</div>
          <div className="mt-1 text-xs text-mute">Past performance of a backtest is not evidence of future results. Educational only.</div>
        </div>)}
    </Shell>
  );
}
