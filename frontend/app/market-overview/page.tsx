"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get } from "@/lib/api";
import { Badge, pct } from "@/lib/ui";

type Ov = { data_mode: string; as_of: string; spy_recent_vol_ann_pct: number | null; spy_regime: string | null; qqq_recent_vol_ann_pct?: number | null; qqq_regime?: string | null;
  regime_counts: Record<string, number>; rising: number; falling: number; earnings_in_window: string[];
  sectors: { sector: string; stocks: number; avg_forecast_vol_ann_pct: number; avg_change_pct: number }[] };

export default function Overview() {
  const [o, setO] = useState<Ov | null>(null);
  const [err, setErr] = useState("");
  const [kes, setKes] = useState<{ data_mode: string; note: string; items: { currency: string; kes_per_unit: number; date: string | null }[] } | null>(null);
  useEffect(() => {
    get<Ov>("/overview").then(setO).catch((e) => setErr(e.message));
    get<NonNullable<typeof kes>>("/fx/kes").then(setKes).catch(() => {});
  }, []);
  const ok = o && o.data_mode === "live-data";
  return (
    <Shell mode={ok ? "live" : ""} asOf={ok ? o.as_of : null}>
      {err && <div className="card text-down">Cannot reach the API ({err}).</div>}
      {o && !ok && <div className="card text-mute tone-brand">No overview yet. Run the weekly refresh so forecasts and prices exist.</div>}
      {ok && (<>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="card tone-info"><div className="text-xs text-mute">Market stress (20-day volatility)</div>
            <div className="mt-1 flex items-center justify-between"><span className="text-sm text-fg2">S&amp;P 500 (SPY)</span>
              <span className="flex items-center gap-2"><span className="text-xl font-semibold">{o.spy_recent_vol_ann_pct ?? "-"}%</span><Badge r={o.spy_regime} /></span></div>
            <div className="mt-1 flex items-center justify-between"><span className="text-sm text-fg2">Nasdaq-100 (QQQ)</span>
              <span className="flex items-center gap-2"><span className="text-xl font-semibold">{o.qqq_recent_vol_ann_pct ?? "-"}%</span><Badge r={o.qqq_regime ?? null} /></span></div></div>
          <div className="card tone-ai"><div className="text-xs text-mute">Forecast risk rising / falling</div>
            <div className="text-2xl font-semibold"><span className="text-info">&#9650; {o.rising}</span> / <span className="text-info">&#9660; {o.falling}</span></div>
            <div className="text-sm text-mute">of {o.rising + o.falling} stocks</div></div>
          <div className="card tone-warn"><div className="text-xs text-mute">Regimes</div>
            <div className="mt-1 flex flex-wrap gap-1">{Object.entries(o.regime_counts).map(([k, v]) => <span key={k} className="text-sm"><Badge r={k} /> {v}</span>)}</div></div>
          <div className="card tone-up"><div className="text-xs text-mute">Earnings in next 5 days</div>
            <div className="text-2xl font-semibold">{o.earnings_in_window.length}</div><div className="text-sm text-mute">{o.earnings_in_window.join(", ") || "none"}</div></div>
        </div>
        {kes && (
          <div className="card tone-warn"><div className="mb-2 font-semibold">Kenya shilling (KES) &mdash; CBK indicative rates</div>
            {kes.data_mode === "none" ? <div className="text-sm text-mute">{kes.note}</div> : (
              <div className="flex flex-wrap gap-6">
                {["USD", "EUR", "GBP", "JPY"].map((c) => kes.items.find((i) => i.currency === c)).filter(Boolean).map((i) => (
                  <div key={i!.currency}><div className="text-xs text-mute">KES per {i!.currency}</div>
                    <div className="text-xl font-semibold">{i!.kes_per_unit.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
                    <div className="text-xs text-mute">{i!.date ?? ""}</div></div>))}
              </div>)}
            <div className="mt-2 text-xs text-mute">Source: Central Bank of Kenya via the Frankfurter API. Indicative daily rates, not executable broker quotes.</div></div>)}
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
