"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get } from "@/lib/api";
import { Badge, pct } from "@/lib/ui";

type Ov = { data_mode: string; as_of: string; spy_recent_vol_ann_pct: number | null; spy_regime: string | null;
  regime_counts: Record<string, number>; rising: number; falling: number; earnings_in_window: string[];
  sectors: { sector: string; stocks: number; avg_forecast_vol_ann_pct: number; avg_change_pct: number }[] };

export default function Overview() {
  const [o, setO] = useState<Ov | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { get<Ov>("/overview").then(setO).catch((e) => setErr(e.message)); }, []);
  const ok = o && o.data_mode === "live-data";
  return (
    <Shell mode={ok ? "live" : ""} asOf={ok ? o.as_of : null}>
      {err && <div className="card text-down">Cannot reach the API ({err}).</div>}
      {o && !ok && <div className="card text-mute tone-brand">No overview yet. Run the weekly refresh so forecasts and prices exist.</div>}
      {ok && (<>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="card tone-info"><div className="text-xs text-mute">Market stress (SPY, 20-day vol)</div>
            <div className="text-2xl font-semibold">{o.spy_recent_vol_ann_pct ?? "-"}%</div><Badge r={o.spy_regime} /></div>
          <div className="card tone-ai"><div className="text-xs text-mute">Forecast risk rising / falling</div>
            <div className="text-2xl font-semibold"><span className="text-info">&#9650; {o.rising}</span> / <span className="text-info">&#9660; {o.falling}</span></div>
            <div className="text-sm text-mute">of {o.rising + o.falling} stocks</div></div>
          <div className="card tone-warn"><div className="text-xs text-mute">Regimes</div>
            <div className="mt-1 flex flex-wrap gap-1">{Object.entries(o.regime_counts).map(([k, v]) => <span key={k} className="text-sm"><Badge r={k} /> {v}</span>)}</div></div>
          <div className="card tone-up"><div className="text-xs text-mute">Earnings in next 5 days</div>
            <div className="text-2xl font-semibold">{o.earnings_in_window.length}</div><div className="text-sm text-mute">{o.earnings_in_window.join(", ") || "none"}</div></div>
        </div>
        <div className="card tone-brand"><div className="mb-2 font-semibold">Forecast risk by sector</div>
          <table className="w-full text-sm"><thead><tr><th className="th">Sector</th><th className="th">Stocks</th><th className="th">Avg forecast vol</th><th className="th">Avg change</th></tr></thead>
            <tbody>{[...o.sectors].sort((a, b) => b.avg_forecast_vol_ann_pct - a.avg_forecast_vol_ann_pct).map((s) => (
              <tr key={s.sector} className="border-t border-line"><td className="py-1.5 font-medium">{s.sector}</td><td>{s.stocks}</td>
                <td>{s.avg_forecast_vol_ann_pct}%</td><td className="text-info">{pct(s.avg_change_pct)}</td></tr>))}</tbody></table>
          <div className="mt-2 text-xs text-mute">Covers the 10 tracked stocks only. Index quotes (S&amp;P 500, Nasdaq, Dow), breadth and movers need a market-data provider and are not shown.</div>
        </div>
      </>)}
    </Shell>
  );
}
