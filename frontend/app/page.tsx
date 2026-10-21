"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarClock, CalendarDays, Gauge, Newspaper, Radar, ShieldCheck, Star, Target, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Chart from "@/components/Chart";
import Title from "@/components/Title";
import Shell from "@/components/Shell";
import { Candle, CandlesResp, Forecast, ForecastsResp, ListResp, Row, get, put } from "@/lib/api";

const RANGES = ["1M", "3M", "6M", "1Y", "5Y"];
const REGIME: Record<string, string> = {
  Calm: "bg-up/15 text-up", Normal: "bg-mute/20 text-fg2",
  Elevated: "bg-warn/20 text-warn", High: "bg-down/20 text-down",
};
const pct = (n: number) => `${n >= 0 ? "\u25B2" : "\u25BC"} ${Math.abs(n)}%`;
const Badge = ({ r }: { r: string | null }) =>
  r ? <span className={`rounded px-2 py-0.5 text-xs ${REGIME[r] ?? ""}`}>{r}</span> : <span className="text-mute">-</span>;

const TONE: Record<string, string> = { brand: "bg-brand/15 text-blue-600 dark:text-blue-400", info: "bg-info/15 text-info", warn: "bg-warn/15 text-warn", ai: "bg-ai/15 text-ai" };
function StatCard({ icon: Icon, tone, label, value, sub, subClass = "text-mute" }: {
  icon: LucideIcon; tone: string; label: string; value: string; sub: string; subClass?: string;
}) {
  return (
    <div className={`card tone-${tone}`}>
      <div className="flex items-start justify-between">
        <div className="text-xs font-medium text-mute">{label}</div>
        <div className={`grid h-9 w-9 place-items-center rounded-xl ${TONE[tone]}`}><Icon className="h-[18px] w-[18px]" /></div>
      </div>
      <div className="mt-2 text-3xl font-bold tracking-tight">{value}</div>
      <div className={`mt-0.5 text-sm ${subClass}`}>{sub}</div>
    </div>
  );
}

export default function Dashboard() {
  const [fc, setFc] = useState<ForecastsResp | null>(null);
  const [wl, setWl] = useState<string[]>([]);
  const [track, setTrack] = useState<ListResp | null>(null);
  const [cal, setCal] = useState<ListResp | null>(null);
  const [sel, setSel] = useState("TSLA");
  const [range, setRange] = useState("1Y");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [cMode, setCMode] = useState("");
  const [cErr, setCErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [sma20, setSma20] = useState(true);
  const [sma50, setSma50] = useState(true);
  const [add, setAdd] = useState("");
  const [tr, setTr] = useState<Record<string, Row>>({});

  useEffect(() => {
    Promise.all([
      get<ForecastsResp>("/forecasts"), get<{ tickers: string[] }>("/watchlist"),
      get<ListResp>("/tracking/summary"), get<ListResp>("/calendar?days=21"), get<ListResp>("/trend"),
    ]).then(([f, w, t, c, trd]) => {
      setFc(f); setWl(w.tickers); setTrack(t); setCal(c);
      setTr(Object.fromEntries(trd.items.map((r) => [String(r.ticker), r])));
      if (f.items.length && !f.items.some((i) => i.ticker === "TSLA")) setSel(f.items[0].ticker);
    }).catch((e) => setErr(`Cannot reach the API (${e.message}). Is the backend running on port 8000?`));
  }, []);

  useEffect(() => {
    setLoading(true); setCErr("");
    get<CandlesResp>(`/candles/${sel}?range=${range}`)
      .then((r) => { setCandles(r.candles); setCMode(r.data_mode); })
      .catch((e) => { setCandles([]); setCErr(e.message); })
      .finally(() => setLoading(false));
  }, [sel, range]);

  const byT = useMemo(() => Object.fromEntries((fc?.items ?? []).map((f) => [f.ticker, f])), [fc]);
  const cur: Forecast | undefined = byT[sel];
  const items = fc?.items ?? [];
  const top = [...items].sort((a, b) => b.forecast_vol_ann_pct - a.forecast_vol_ann_pct)[0];
  const rise = [...items].sort((a, b) => b.change_pct - a.change_pct)[0];
  const earn = items.filter((i) => i.earnings_in_window);
  const live = track?.items.find((r) => r.source === "live") ?? track?.items.find((r) => r.source === "all");
  const radar = [...items].sort((a, b) => Number(b.earnings_in_window) - Number(a.earnings_in_window) || b.change_pct - a.change_pct);

  const saveWl = useCallback((next: string[]) => {
    put<{ tickers: string[] }>("/watchlist", { tickers: next }).then((r) => setWl(r.tickers)).catch((e) => setErr(e.message));
  }, []);

  return (
    <Shell mode={fc?.data_mode ?? ""} asOf={fc?.as_of ?? null} tickers={items.map((i) => i.ticker)} onPick={setSel}>
      {err && <div className="card border-down text-down">{err}</div>}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={Gauge} tone="brand" label="Highest expected risk" value={top?.ticker ?? "-"}
          sub={top ? `${top.forecast_vol_ann_pct}% annualized` : ""} />
        <StatCard icon={TrendingUp} tone="info" label="Biggest forecast rise" value={rise?.ticker ?? "-"}
          sub={rise ? pct(rise.change_pct) + " vs recent" : ""} subClass="text-info" />
        <StatCard icon={CalendarClock} tone="warn" label="Earnings in next 5 days" value={String(earn.length)}
          sub={earn.map((e) => e.ticker).join(", ") || "none"} />
        <StatCard icon={ShieldCheck} tone="ai" label="Forecasts closer than naive" value={live ? `${live.closer_than_naive_pct}%` : "-"}
          sub={live ? `${live.forecasts} scored (${live.source})` : "no scored forecasts yet"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card tone-brand lg:col-span-2">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <div className="text-lg font-semibold">{sel}</div>
            {cMode === "demo" && <span className="rounded bg-warn/20 px-2 py-0.5 text-xs text-warn">DEMO prices</span>}
            <div className="ml-auto flex gap-1">
              {RANGES.map((r) => (
                <button key={r} onClick={() => setRange(r)}
                  className={`rounded px-2 py-1 text-xs ${r === range ? "bg-brand text-white" : "text-mute hover:text-fg"}`}>{r}</button>
              ))}
              <button onClick={() => setSma20(!sma20)} className={`rounded px-2 py-1 text-xs ${sma20 ? "text-info" : "text-mute"}`}>SMA20</button>
              <button onClick={() => setSma50(!sma50)} className={`rounded px-2 py-1 text-xs ${sma50 ? "text-warn" : "text-mute"}`}>SMA50</button>
            </div>
          </div>
          {loading ? <div className="flex h-[360px] items-center justify-center text-mute">Loading chart...</div>
            : cErr ? <div className="flex h-[360px] items-center justify-center text-down">No price data for {sel} ({cErr})</div>
            : <Chart candles={candles} sma20={sma20} sma50={sma50} />}
        </div>

        <div className="card tone-ai">
          <div className="mb-3 flex items-center justify-between"><Title icon={Gauge} tone="ai" mb="">Volatility forecast</Title>
            <span className="rounded bg-ai/15 px-2 py-0.5 text-xs text-ai">Ensemble model</span></div>
          {cur ? (<>
            <div className="text-xs text-mute">Expected size of swings, next 5 trading days</div>
            <div className="w-fit bg-gradient-to-r from-blue-500 to-violet-500 bg-clip-text text-5xl font-bold tracking-tight text-transparent">{cur.forecast_vol_ann_pct}%</div>
            <div className="mb-3 text-sm text-mute">annualized (about {cur.typical_daily_move_pct}% per day)</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-mute">Recent (20 days)</span><span>{cur.recent_vol_ann_pct}%</span></div>
              <div className="flex justify-between"><span className="text-mute">Change vs recent</span>
                <span className="text-info">{pct(cur.change_pct)}</span></div>
              <div className="flex justify-between"><span className="text-mute">Regime vs own history</span><Badge r={cur.regime} /></div>
              <div className="flex justify-between"><span className="text-mute">Next earnings</span>
                <span>{cur.next_earnings ?? "-"}{cur.earnings_in_window && <span className="ml-1 text-warn">&#9733; in window</span>}</span></div>
            </div>
            {tr[sel] && (
              <div className="mt-4 border-t border-line pt-3 text-sm">
                <div className="mb-1 flex items-center justify-between"><span className="font-semibold">Trend context</span>
                  <span className={tr[sel].label === "Uptrend" ? "text-up" : tr[sel].label === "Downtrend" ? "text-down" : "text-mute"}>{String(tr[sel].label)}</span></div>
                {([["vs 50-day avg", "vs_sma50_pct"], ["vs 200-day avg", "vs_sma200_pct"], ["1 month", "ret_1m_pct"], ["3 months", "ret_3m_pct"], ["From 52-week high", "off_52w_high_pct"]] as const).map(([lbl, k]) => {
                  const v = Number(tr[sel][k]);
                  return (<div key={k} className="flex justify-between"><span className="text-mute">{lbl}</span>
                    <span className={v > 0 ? "text-up" : v < 0 ? "text-down" : ""}>{v > 0 ? "+" : ""}{v}%</span></div>);
                })}
                <div className="mt-1 text-xs text-mute">Describes where the price has been. It is not a forecast of direction.</div>
              </div>)}
            <div className="mt-3 text-xs text-mute">&#9650; = expected risk up, &#9660; = down. This describes risk, not a price call.</div>
          </>) : <div className="text-sm text-mute">No forecast for {sel}.</div>}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card tone-brand" id="watchlist">
          <Title icon={Star} tone="brand">Watchlist</Title>
          <table className="w-full text-sm"><thead><tr><th className="th">Ticker</th><th className="th">Forecast</th><th className="th">Change</th><th className="th">Regime</th><th /></tr></thead>
            <tbody>{wl.map((t) => { const f = byT[t]; return (
              <tr key={t} className="cursor-pointer border-t border-line hover:bg-fg/5" onClick={() => setSel(t)}>
                <td className="py-1.5 font-medium">{t}</td><td>{f ? `${f.forecast_vol_ann_pct}%` : "-"}</td>
                <td className="text-info">{f ? pct(f.change_pct) : "-"}</td>
                <td><Badge r={f?.regime ?? null} /></td>
                <td><button className="text-mute hover:text-down" onClick={(e) => { e.stopPropagation(); saveWl(wl.filter((x) => x !== t)); }}>&times;</button></td>
              </tr>); })}</tbody></table>
          <input value={add} onChange={(e) => setAdd(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === "Enter" && add) { saveWl([...wl, add]); setAdd(""); } }}
            placeholder="Add ticker + Enter" className="mt-2 w-full rounded border border-line bg-bg px-2 py-1 text-sm outline-none" />
        </div>

        <div className="card tone-warn">
          <Title icon={Radar} tone="warn">Risk radar</Title>
          <div className="mb-2 text-xs text-mute">Earnings first, then biggest forecast rise</div>
          {radar.slice(0, 6).map((f) => (
            <div key={f.ticker} onClick={() => setSel(f.ticker)} className="flex cursor-pointer items-center justify-between border-t border-line py-1.5 text-sm hover:bg-fg/5">
              <span className="font-medium">{f.ticker}{f.earnings_in_window && <span className="ml-1 text-warn">&#9733;</span>}</span>
              <span className="text-mute">{f.forecast_vol_ann_pct}%</span>
              <span className="text-info">{pct(f.change_pct)}</span>
            </div>))}
        </div>

        <div className="card tone-ai">
          <Title icon={CalendarDays} tone="ai">Upcoming events (21 days)</Title>
          {cal?.items.length ? cal.items.slice(0, 8).map((e, i) => (
            <div key={i} className="flex justify-between border-t border-line py-1.5 text-sm">
              <span className="text-mute">{String(e.date)}</span><span>{e.ticker ? `${e.ticker} earnings` : String(e.type)}</span></div>))
            : <div className="text-sm text-mute">No events found. Run build_events.py and fetch_earnings.py.</div>}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card tone-up lg:col-span-2">
          <Title icon={Target} tone="up">Forecast tracking (scored on what actually happened)</Title>
          {track?.items.length ? (
            <table className="w-full text-sm"><thead><tr>{["Set", "Scored", "Model err", "Naive err", "Closer than naive", "Direction hit"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>{track.items.map((r) => (
                <tr key={String(r.source)} className="border-t border-line"><td className="py-1.5">{String(r.source)}</td><td>{r.forecasts}</td>
                  <td>{r.ens_mae}</td><td>{r.naive_mae}</td><td>{r.closer_than_naive_pct}%</td><td>{r.direction_hit_pct}%</td></tr>))}</tbody></table>
          ) : <div className="text-sm text-mute">No tracking results yet. Run track_forecasts.py.</div>}
          <div className="mt-2 text-xs text-mute">&ldquo;live&rdquo; = saved in real time; &ldquo;backfill&rdquo; = rebuilt from past data (not a live record).</div>
        </div>
        <div className="card tone-info"><Title icon={Newspaper} tone="info">News &amp; sentiment</Title>
          <div className="text-sm text-mute">No news provider connected, so nothing is shown. Headlines will appear here once a licensed news source is configured.</div></div>
      </div>
    </Shell>
  );
}
