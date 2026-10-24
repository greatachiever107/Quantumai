"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { API, Row, get } from "@/lib/api";

type Health = { status: string; project_dir: string; files_found: Record<string, boolean>; mode: string; news_configured?: boolean };

export default function Settings() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState("");
  const [src, setSrc] = useState<Row[]>([]);
  useEffect(() => {
    get<Health>("/health").then(setH).catch((e) => setErr(e.message));
    get<{ items: Row[] }>("/sources").then((r) => setSrc(r.items)).catch(() => {});
  }, []);
  return (
    <Shell mode={h?.mode === "demo" ? "demo" : "live"} asOf={null}>
      <div className="card tone-brand">
        <div className="mb-2 text-lg font-semibold">System status</div>
        {err ? <div className="text-down">API unreachable at {API} ({err})</div> : !h ? <div className="text-mute">Checking...</div> : (
          <div className="space-y-1 text-sm">
            <div><span className="text-mute">API: </span>{API} &mdash; <span className="text-up">{h.status}</span></div>
            <div><span className="text-mute">Data mode: </span>{h.mode}</div>
            <div><span className="text-mute">News feed: </span>{h.news_configured ? <span className="text-up">key configured</span> : <span className="text-warn">no key set (add FINNHUB_API_KEY)</span>}</div>
            <div><span className="text-mute">Project folder: </span>{h.project_dir}</div>
            <div className="pt-2 text-mute">Result files found:</div>
            {Object.entries(h.files_found).map(([k, v]) => (
              <div key={k} className="pl-3">{v ? <span className="text-up">&#10003;</span> : <span className="text-down">&#10007;</span>} {k.replace("_", " ")}</div>))}
          </div>)}
      </div>
      {src.length > 0 && (
        <div className="card tone-ai overflow-x-auto">
          <div className="mb-2 text-lg font-semibold">Data sources</div>
          <table className="w-full text-sm"><thead><tr>{["Source", "Covers", "Free limits", "Freshness", "Public redistribution", "In this app"].map((h) => <th key={h} className="th pr-3">{h}</th>)}</tr></thead>
            <tbody>{src.map((s) => (
              <tr key={String(s.id)} className="border-t border-line align-top">
                <td className="py-2 pr-3 font-medium">{String(s.name)}</td><td className="pr-3">{String(s.assets)}</td>
                <td className="pr-3 text-fg2">{String(s.limits)}</td><td className="pr-3">{String(s.freshness)}</td>
                <td className={`pr-3 ${String(s.redistribution).startsWith("No") ? "text-warn" : ""}`}>{String(s.redistribution)}</td>
                <td className="text-fg2">{String(s.status)}</td></tr>))}</tbody></table>
          <div className="mt-2 text-xs text-mute">Free tiers can change. Prices here are end-of-day; none of this is licensed for public redistribution unless stated.</div>
        </div>)}
      <div className="card text-sm text-fg2 tone-info">
        <div className="mb-2 text-lg font-semibold">Refresh the data</div>
        Run <code className="rounded bg-bg px-1">python run_weekly.py</code> in the project folder to download new prices, events and earnings,
        rescore forecasts and rebuild everything. This page and the dashboard then show the new numbers.
        <div className="mt-3 text-xs text-mute">Login, per-user preferences, timezone and notification settings arrive with the deployment step.</div>
      </div>
    </Shell>
  );
}
