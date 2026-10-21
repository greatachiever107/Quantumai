"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { ListResp, Row, get } from "@/lib/api";

function Table({ rows, first }: { rows: Row[]; first: string }) {
  if (!rows.length) return <div className="text-sm text-mute">No data yet.</div>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>{cols.map((c) => <th key={c} className="th pr-3 whitespace-nowrap">{c.replace(/_/g, " ")}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => (<tr key={i} className="border-t border-line">{cols.map((c) =>
        <td key={c} className={`py-1.5 pr-3 ${c === first ? "font-medium" : ""}`}>{String(r[c] ?? "-")}</td>)}</tr>))}</tbody></table></div>
  );
}

export default function ModelLab() {
  const [sum, setSum] = useState<ListResp | null>(null);
  const [by, setBy] = useState<ListResp | null>(null);
  const [trk, setTrk] = useState<ListResp | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    Promise.all([get<ListResp>("/models/summary"), get<ListResp>("/models/by-stock"), get<ListResp>("/tracking/summary")])
      .then(([a, b, c]) => { setSum(a); setBy(b); setTrk(c); }).catch((e) => setErr(e.message));
  }, []);
  return (
    <Shell mode="live" asOf={null}>
      {err && <div className="card text-down">Cannot reach the API ({err}).</div>}
      <div className="card tone-brand">
        <div className="mb-2 flex items-center gap-2 text-lg font-semibold">Production model <span className="rounded bg-ai/15 px-2 py-0.5 text-xs font-normal text-ai">Ensemble v3</span></div>
        <div className="grid gap-3 text-sm text-fg2 md:grid-cols-2">
          <div><span className="text-mute">Target: </span>standard deviation of daily returns over the next 5 trading days (volatility). Direction is not predicted.</div>
          <div><span className="text-mute">Models: </span>average of EWMA volatility, a pooled ridge regression and a pooled gradient-boosting model, all trained on every stock together.</div>
          <div><span className="text-mute">Inputs: </span>close-to-close and High-Low range volatility, overnight gaps, 1-year level, SPY market stress, FOMC/NFP in the window, and per-stock earnings (next 5 / last 5 / last 20 days).</div>
          <div><span className="text-mute">Validation: </span>walk-forward, 5 folds with a 5-day gap; scalers and bias corrections fit on training data only; every method compared with a naive baseline.</div>
        </div>
      </div>
      <div className="card tone-info"><div className="mb-2 font-semibold">Backtest scorecard (lower is better)</div><Table rows={sum?.items ?? []} first="method" />
        <div className="mt-2 text-xs text-mute">MAE = average error in daily-volatility %, QLIKE = a standard volatility loss that punishes under-forecasting.</div></div>
      <div className="card tone-ai"><div className="mb-2 font-semibold">Average error by stock</div><Table rows={by?.items ?? []} first="Ticker" /></div>
      <div className="card tone-warn"><div className="mb-2 font-semibold">Forecast tracking</div><Table rows={trk?.items ?? []} first="source" />
        <div className="mt-2 text-xs text-mute">{trk?.note}</div></div>
    </Shell>
  );
}
