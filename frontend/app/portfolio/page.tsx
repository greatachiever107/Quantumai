"use client";
import { useEffect, useMemo, useState } from "react";
import Shell from "@/components/Shell";
import { ForecastsResp, ListResp, get } from "@/lib/api";

export default function Portfolio() {
  const [fc, setFc] = useState<ForecastsResp | null>(null);
  const [qt, setQt] = useState<Record<string, number>>({});
  const [cap, setCap] = useState(10000);
  const [mode, setMode] = useState<"forecast" | "equal">("forecast");
  const [err, setErr] = useState("");
  useEffect(() => {
    Promise.all([get<ForecastsResp>("/forecasts"), get<ListResp>("/quotes")]).then(([f, q]) => {
      setFc(f); setQt(Object.fromEntries(q.items.map((r) => [String(r.ticker), Number(r.close)])));
    }).catch((e) => setErr(e.message));
  }, []);
  const rows = useMemo(() => {
    const it = fc?.items ?? [];
    const inv = it.map((f) => 1 / f.forecast_vol_ann_pct);
    const sum = inv.reduce((a, b) => a + b, 0);
    const base = it.map((f, i) => {
      const w = mode === "equal" ? 1 / it.length : inv[i] / sum;
      const price = qt[f.ticker] ?? 0;
      const shares = price > 0 ? Math.floor((cap * w) / price) : 0;
      return { f, w, price, shares, invested: shares * price, risk: w * f.forecast_vol_ann_pct };
    });
    const rs = base.reduce((a, b) => a + b.risk, 0) || 1;
    return base.map((r) => ({ ...r, riskShare: (r.risk / rs) * 100 })).sort((a, b) => b.w - a.w);
  }, [fc, qt, cap, mode]);
  const invested = rows.reduce((a, r) => a + r.invested, 0);
  const wAvg = rows.reduce((a, r) => a + r.w * r.f.forecast_vol_ann_pct, 0);
  const $ = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return (
    <Shell mode={fc?.data_mode ?? ""} asOf={fc?.as_of ?? null}>
      {err && <div className="card text-down">Cannot reach the API ({err}).</div>}
      <div className="card border-warn/40 text-sm text-warn tone-warn">SIMULATED PORTFOLIO &mdash; a planning tool. No orders are placed and no broker is connected. Prices are end-of-day closes.</div>
      <div className="card tone-brand">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <div className="text-lg font-semibold">Risk-sized portfolio</div>
          <label className="text-sm text-mute">Capital $ <input type="number" min={100} value={cap} onChange={(e) => setCap(Math.max(100, Number(e.target.value)))}
            className="ml-1 w-28 rounded border border-line bg-bg px-2 py-1 text-fg outline-none" /></label>
          {(["forecast", "equal"] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)} className={`rounded px-3 py-1 text-sm ${mode === m ? "bg-brand text-white" : "text-mute"}`}>
              {m === "forecast" ? "Sized by forecast risk" : "Equal weight"}</button>))}
        </div>
        <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <div><div className="text-xs text-mute">Invested</div><div className="text-xl font-semibold">${$(invested)}</div></div>
          <div><div className="text-xs text-mute">Cash left (rounding)</div><div className="text-xl font-semibold">${$(cap - invested)}</div></div>
          <div><div className="text-xs text-mute">Weighted avg forecast vol</div><div className="text-xl font-semibold">{wAvg.toFixed(1)}%</div></div>
          <div><div className="text-xs text-mute">Largest risk share</div><div className="text-xl font-semibold">{rows[0] ? Math.max(...rows.map((r) => r.riskShare)).toFixed(0) : 0}%</div></div>
        </div>
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>
          {["Ticker", "Weight", "Dollars", "Price", "Shares", "Forecast vol", "Risk share"].map((h) => <th key={h} className="th pr-3">{h}</th>)}</tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.f.ticker} className="border-t border-line"><td className="py-1.5 font-medium">{r.f.ticker}</td>
              <td>{(r.w * 100).toFixed(1)}%</td><td>${$(cap * r.w)}</td><td>{r.price ? `$${r.price.toFixed(2)}` : "-"}</td>
              <td>{r.shares}</td><td>{r.f.forecast_vol_ann_pct}%</td><td>{r.riskShare.toFixed(0)}%</td></tr>))}</tbody></table></div>
        <div className="mt-3 text-xs text-mute">Forecast sizing gives each stock weight proportional to 1 / forecast volatility, so riskier stocks get smaller slices.
          Risk share = weight &times; forecast vol, an approximation that ignores correlations. The backtest showed this lowers volatility but not
          necessarily improves returns. Educational only &mdash; not financial advice.</div>
      </div>
    </Shell>
  );
}
