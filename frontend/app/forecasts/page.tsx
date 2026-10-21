"use client";
import { useEffect, useMemo, useState } from "react";
import { TrendingUp } from "lucide-react";
import Shell from "@/components/Shell";
import Title from "@/components/Title";
import { Forecast, ForecastsResp, ListResp, Row, get } from "@/lib/api";
import { Badge, pct } from "@/lib/ui";

type Key = keyof Forecast;
const COLS: [string, Key][] = [["Ticker", "ticker"], ["Recent vol %", "recent_vol_ann_pct"], ["Forecast vol %", "forecast_vol_ann_pct"],
  ["Change", "change_pct"], ["Daily move %", "typical_daily_move_pct"], ["Regime", "regime"], ["Next earnings", "next_earnings"]];

export default function Forecasts() {
  const [d, setD] = useState<ForecastsResp | null>(null);
  const [err, setErr] = useState("");
  const [key, setKey] = useState<Key>("forecast_vol_ann_pct");
  const [desc, setDesc] = useState(true);
  const [q, setQ] = useState("");
  const [onlyEarn, setOnlyEarn] = useState(false);
  const [tr, setTr] = useState<Record<string, Row>>({});
  useEffect(() => {
    get<ForecastsResp>("/forecasts").then(setD).catch((e) => setErr(e.message));
    get<ListResp>("/trend").then((r) => setTr(Object.fromEntries(r.items.map((x) => [String(x.ticker), x])))).catch(() => {});
  }, []);
  const rows = useMemo(() => {
    const r = (d?.items ?? []).filter((x) => x.ticker.includes(q) && (!onlyEarn || x.earnings_in_window));
    return r.sort((a, b) => {
      const x = a[key] ?? "", y = b[key] ?? "";
      return (x < y ? -1 : x > y ? 1 : 0) * (desc ? -1 : 1);
    });
  }, [d, key, desc, q, onlyEarn]);
  return (
    <Shell mode={d?.data_mode ?? ""} asOf={d?.as_of ?? null}>
      {err && <div className="card text-down">Cannot reach the API ({err}).</div>}
      <div className="card tone-brand">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <Title icon={TrendingUp} tone="brand" mb="">Volatility forecasts</Title>
          <input value={q} onChange={(e) => setQ(e.target.value.toUpperCase())} placeholder="Filter ticker"
            className="rounded border border-line bg-bg px-2 py-1 text-sm outline-none" />
          <label className="flex items-center gap-1 text-sm text-mute">
            <input type="checkbox" checked={onlyEarn} onChange={(e) => setOnlyEarn(e.target.checked)} /> Earnings in window only</label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm"><thead><tr>
            {COLS.map(([h, k]) => (
              <th key={h} className="th cursor-pointer whitespace-nowrap pr-4" onClick={() => { if (k === key) setDesc(!desc); else { setKey(k); setDesc(true); } }}>
                {h}{k === key ? (desc ? " \u25BC" : " \u25B2") : ""}</th>))}
            <th className="th whitespace-nowrap pr-4">Trend</th><th className="th whitespace-nowrap pr-4">3M price</th>
          </tr></thead><tbody>
            {rows.map((f) => (
              <tr key={f.ticker} className="border-t border-line">
                <td className="py-2 font-medium">{f.ticker}{f.earnings_in_window && <span className="ml-1 text-warn">&#9733;</span>}</td>
                <td>{f.recent_vol_ann_pct}</td><td>{f.forecast_vol_ann_pct}</td>
                <td className="text-info">{pct(f.change_pct)}</td>
                <td>{f.typical_daily_move_pct}</td><td><Badge r={f.regime} /></td><td>{f.next_earnings ?? "-"}</td>
                <td className={tr[f.ticker]?.label === "Uptrend" ? "text-up" : tr[f.ticker]?.label === "Downtrend" ? "text-down" : "text-mute"}>{String(tr[f.ticker]?.label ?? "-")}</td>
                <td className={Number(tr[f.ticker]?.ret_3m_pct) > 0 ? "text-up" : Number(tr[f.ticker]?.ret_3m_pct) < 0 ? "text-down" : ""}>{tr[f.ticker] ? `${Number(tr[f.ticker].ret_3m_pct) > 0 ? "+" : ""}${tr[f.ticker].ret_3m_pct}%` : "-"}</td>
              </tr>))}
          </tbody></table>
        </div>
        <div className="mt-3 text-xs text-mute">{d?.note} Click a column header to sort. &#9733; = earnings inside the 5-day window. Trend and 3M price describe the past, not the future.</div>
      </div>
    </Shell>
  );
}
