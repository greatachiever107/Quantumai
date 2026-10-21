"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useState } from "react";
import { Activity, BarChart3, Cpu, FlaskConical, LayoutDashboard, Moon, Newspaper, Search, Settings, Star, Sun, TrendingUp, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTheme } from "@/lib/theme";

const NAV: [string, string, LucideIcon, string][] = [
  ["Dashboard", "/", LayoutDashboard, "Risk forecasts, trend context and tracked accuracy at a glance"],
  ["Market Overview", "/market-overview", BarChart3, "Market stress and forecast risk across sectors"],
  ["Forecasts", "/forecasts", TrendingUp, "Next-5-day volatility forecast for every tracked stock"],
  ["Watchlist", "/#watchlist", Star, "Your tracked stocks"],
  ["Portfolio", "/portfolio", Wallet, "A simulated portfolio sized by forecast risk"],
  ["Backtesting", "/backtesting", FlaskConical, "How risk-based position sizing performed historically"],
  ["News & Sentiment", "/news", Newspaper, "Headlines and sentiment from a connected news source"],
  ["Model Lab", "/model-lab", Cpu, "How the forecasting model works and how well it performs"],
  ["Settings", "/settings", Settings, "System status and data refresh"],
];

export default function Shell({ children, mode, asOf, tickers = [], onPick = () => {} }: {
  children: ReactNode; mode: string; asOf: string | null; tickers?: string[]; onPick?: (t: string) => void;
}) {
  const [q, setQ] = useState("");
  const path = usePathname();
  const theme = useTheme();
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    try { localStorage.setItem("theme", next); } catch {}
  };
  const cur = NAV.find((n) => n[1] === path) ?? NAV[0];
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-panel/80 p-4 backdrop-blur md:flex">
        <div className="mb-8 flex items-center gap-3 px-1">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-brand to-ai text-white shadow-lg shadow-brand/30"><Activity className="h-5 w-5" /></div>
          <div><div className="text-xl font-bold leading-none">Stock<span className="text-brand">AI</span></div>
            <div className="mt-1 text-[11px] text-mute">Volatility intelligence</div></div>
        </div>
        <nav className="space-y-1">
          {NAV.map(([n, href, Icon]) => {
            const active = path === href;
            return (
              <Link key={n} href={href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${active
                ? "bg-gradient-to-r from-brand to-ai text-white shadow-md shadow-brand/25" : "text-fg2 hover:bg-fg/5"}`}>
                <Icon className={`h-[18px] w-[18px] ${active ? "text-white" : "text-mute"}`} />{n}
              </Link>);
          })}
        </nav>
        <div className="mt-auto rounded-xl border border-line bg-bg/60 p-3 text-[11px] leading-relaxed text-mute">
          Forecasts describe the <b className="text-fg2">size</b> of price swings, not direction. Educational only &mdash; not financial advice.
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center gap-3 border-b border-line bg-panel/60 px-6 py-3 backdrop-blur">
          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" />
            <input list="tk" value={q} onChange={(e) => setQ(e.target.value.toUpperCase())}
              onKeyDown={(e) => { if (e.key === "Enter" && q) { onPick(q); setQ(""); } }}
              placeholder="Search ticker, press Enter"
              className="w-full rounded-xl border border-line bg-bg/60 py-2 pl-9 pr-3 text-sm outline-none focus:border-brand" />
          </div>
          <datalist id="tk">{tickers.map((t) => <option key={t} value={t} />)}</datalist>
          <div className="ml-auto flex items-center gap-3 text-xs">
            {mode === "demo"
              ? <span className="rounded-full bg-warn/20 px-3 py-1 font-semibold text-warn">DEMO DATA - not real</span>
              : <span className="flex items-center gap-1.5 rounded-full bg-up/15 px-3 py-1 font-medium text-up"><span className="h-1.5 w-1.5 rounded-full bg-up" />Project data</span>}
            <span className="hidden text-mute sm:inline">{asOf ? `Prices through ${asOf} (end of day)` : ""}</span>
            <button onClick={toggle} aria-label="Toggle light or dark theme"
              className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-panel text-fg2 hover:bg-fg/5">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>
        <main className="space-y-5 p-6">
          <div><h1 className="text-2xl font-bold tracking-tight">{cur[0]}</h1><p className="mt-0.5 text-sm text-mute">{cur[3]}</p></div>
          {children}
        </main>
        <footer className="px-6 pb-6 text-xs text-mute">Educational only - not financial advice. Prices from Yahoo Finance via yfinance (development use).</footer>
      </div>
    </div>
  );
}
