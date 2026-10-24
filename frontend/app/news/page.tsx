"use client";
import { useEffect, useMemo, useState } from "react";
import { Newspaper } from "lucide-react";
import NewsList from "@/components/NewsList";
import Shell from "@/components/Shell";
import Title from "@/components/Title";
import { NewsResp, get } from "@/lib/api";

export default function News() {
  const [d, setD] = useState<NewsResp | null>(null);
  const [err, setErr] = useState("");
  const [tk, setTk] = useState("");
  const [sent, setSent] = useState("");
  useEffect(() => { get<NewsResp>("/news?limit=100").then(setD).catch((e) => setErr(e.message)); }, []);
  const tickers = useMemo(() => Array.from(new Set((d?.items ?? []).flatMap((i) => i.tickers.map((t) => t.ticker)))).sort(), [d]);
  const rows = useMemo(() => (d?.items ?? []).map((i) => {
    if (!tk) return i;
    const t = i.tickers.find((x) => x.ticker === tk);
    return t ? { ...i, sentiment: t.sentiment, score: t.score } : null;
  }).filter((i): i is NonNullable<typeof i> => i !== null && (!sent || i.sentiment === sent)), [d, tk, sent]);
  const sel = "rounded-lg border border-line bg-bg/60 px-2 py-1.5 text-sm outline-none";
  return (
    <Shell mode={d ? (d.data_mode === "none" ? "live" : "live") : ""} asOf={null}>
      {err && <div className="card text-down">Cannot reach the API ({err}).</div>}
      <div className="card tone-info">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <Title icon={Newspaper} tone="info" mb="">Latest news on your stocks</Title>
          <select value={tk} onChange={(e) => setTk(e.target.value)} className={sel}>
            <option value="">All tickers</option>{tickers.map((t) => <option key={t}>{t}</option>)}</select>
          <select value={sent} onChange={(e) => setSent(e.target.value)} className={sel}>
            <option value="">Any sentiment</option><option>Positive</option><option>Negative</option><option>Neutral</option></select>
        </div>
        {!d && !err && <div className="text-sm text-mute">Loading headlines...</div>}
        {d && d.data_mode === "none" && <div className="text-sm text-fg2">{d.note}</div>}
        {d && d.data_mode !== "none" && rows.length === 0 && <div className="text-sm text-mute">No articles match these filters right now.</div>}
        {d && d.summary && d.data_mode !== "none" && <div className="mb-3 rounded-xl bg-fg/5 px-3 py-2 text-sm text-fg2">{d.summary}</div>}
        {rows.length > 0 && <NewsList items={rows} />}
        {d && d.data_mode !== "none" && (
          <div className="mt-4 border-t border-line pt-3 text-xs text-mute">
            {d.note} Source: {d.source}. Headlines link to the original publisher.
            {d.stale && " Showing the last successful update because the provider is temporarily unavailable."}
          </div>)}
      </div>
    </Shell>
  );
}
