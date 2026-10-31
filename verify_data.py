"""Independent checks on the numbers the site shows.

    python verify_data.py
Run from the project folder, after run_weekly.py (and ideally after the US market has closed).
It re-computes the key numbers from the raw price file with separate code and compares them with
what the app serves. Optional: set FINNHUB_API_KEY to also compare closing prices with a second source.
Exit code 1 if any check FAILS. Educational tool - it proves the arithmetic, not that forecasts will be right.
"""
import os
import sys
import json
import urllib.request

import numpy as np
import pandas as pd

os.environ.setdefault("PROJECT_DIR", os.getcwd())
sys.path.insert(0, os.getcwd())
rows = []


def check(name, status, detail=""):
    rows.append((status, name, detail))


px = pd.read_csv("data/stocks.csv", parse_dates=["Date"]).sort_values(["Ticker", "Date"])
funds = {"SPY", "QQQ"}

# ---------- 1. raw price file sanity ----------
bad = px[["Open", "High", "Low", "Close"]].isna().any(axis=1).sum() + (px["Close"] <= 0).sum()
check("No missing or non-positive prices", "PASS" if bad == 0 else "FAIL", f"{bad} bad rows")
tol = 1e-6 * px["Close"]
viol = ((px["High"] + tol < px["Low"]) | (px["Close"] > px["High"] + tol * 1e3) | (px["Close"] < px["Low"] - tol * 1e3)).sum()
check("High >= Low and Close inside the day's range", "PASS" if viol == 0 else "FAIL", f"{viol} rows violate")
dups = px.duplicated(["Date", "Ticker"]).sum()
check("No duplicate (date, ticker) rows", "PASS" if dups == 0 else "FAIL", f"{dups} duplicates")
latest = px["Date"].max()
age = (pd.Timestamp.now().normalize() - latest).days
check("Prices are recent (<= 5 days old)", "PASS" if age <= 5 else "WARN", f"latest {latest.date()} ({age} days ago)")
stale = [t for t, d in px.groupby("Ticker")["Date"].max().items() if d != latest]
check("Every ticker reaches the same latest date", "PASS" if not stale else "FAIL", f"behind: {stale}")
gaps = {t: int(g["Date"].diff().dt.days.max()) for t, g in px.groupby("Ticker")}
check("No gaps over 7 days in any history", "PASS" if max(gaps.values()) <= 7 else "WARN", f"largest gap {max(gaps.values())} days")
rec = px.groupby("Ticker")["Close"].pct_change() * 100
diff = (rec - px["daily_return_pct"]).abs().max()
check("Stored daily returns match prices", "PASS" if diff < 1e-6 else "FAIL", f"max difference {diff:.2e}")
big = px.loc[px["daily_return_pct"].abs() > 30, ["Date", "Ticker", "daily_return_pct"]]
check("Extreme one-day moves (>30%) reviewed", "PASS" if big.empty else "WARN",
      "none" if big.empty else "; ".join(f"{r.Ticker} {r.Date.date()} {r.daily_return_pct:.0f}%" for r in big.itertuples()))

# ---------- 2. recent volatility vs the forecast file ----------
f = pd.read_csv("output/processed/volatility_forecast.csv")
wrong = []
for r in f.itertuples():
    ret = px.loc[px["Ticker"] == r.Ticker, "daily_return_pct"].tail(20)
    mine = ret.std(ddof=1) * np.sqrt(252)
    if abs(mine - r.recent_20d_vol_ann_pct) > 0.2:
        wrong.append(f"{r.Ticker}: site {r.recent_20d_vol_ann_pct} vs recomputed {mine:.1f}")
check("20-day volatility matches an independent calculation", "PASS" if not wrong else "FAIL", "; ".join(wrong) or f"{len(f)} tickers")

# ---------- 3. trend numbers and indicators vs independent code ----------
try:
    import backend.main as m
    trend = {i["ticker"]: i for i in m.trend()["items"]}
    tw, iw = [], []
    for t, g in px.groupby("Ticker"):
        c = g["Close"].to_numpy()
        if len(c) < 210 or t not in trend:
            continue
        mine = {"vs_sma50_pct": (c[-1] / c[-50:].mean() - 1) * 100, "vs_sma200_pct": (c[-1] / c[-200:].mean() - 1) * 100,
                "ret_3m_pct": (c[-1] / c[-64] - 1) * 100, "off_52w_high_pct": (c[-1] / c[-252:].max() - 1) * 100}
        for k, v in mine.items():
            if abs(v - trend[t][k]) > 0.06:
                tw.append(f"{t} {k}: site {trend[t][k]} vs {v:.2f}")
        # RSI(14) by Wilder's recursion, written as a plain loop (independent of the pandas version)
        d = np.diff(c)
        g_, l_ = np.maximum(d, 0), np.maximum(-d, 0)
        ag, al = g_[:14].mean(), l_[:14].mean()
        for x, y in zip(g_[14:], l_[14:]):
            ag, al = (ag * 13 + x) / 14, (al * 13 + y) / 14
        rsi = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        site = m.indicators_for(t)["rsi14"]
        if abs(rsi - site) > 0.1:
            iw.append(f"{t}: site {site} vs {rsi:.1f}")
    check("Trend numbers (50/200-day, 3-month, 52-week) re-computed", "PASS" if not tw else "FAIL", "; ".join(tw[:4]) or f"{len(trend)} tickers")
    check("RSI(14) matches a plain-loop implementation", "PASS" if not iw else "FAIL", "; ".join(iw[:4]) or "all tickers")
except Exception as e:                                           # noqa
    check("Trend/indicator re-computation", "WARN", f"could not run: {str(e)[:100]}")

# ---------- 4. forecast tracking audit ----------
sp = "output/tracking/forecast_scored.csv"
if os.path.exists(sp):
    sc = pd.read_csv(sp, parse_dates=["as_of"])
    bad_real, bad_win = [], 0
    for r in sc.itertuples():
        g = px[px["Ticker"] == r.Ticker].reset_index(drop=True)
        i = g.index[g["Date"] == r.as_of]
        if len(i) == 0 or i[0] + 5 >= len(g):
            bad_win += 1
            continue
        real = g["daily_return_pct"].iloc[i[0] + 1:i[0] + 6].std(ddof=1)
        if abs(real - r.realized_daily_vol) > 1e-6:
            bad_real.append(f"{r.Ticker} {r.as_of.date()}")
    check("Scored forecasts: realized volatility re-computed", "PASS" if not bad_real else "FAIL", "; ".join(bad_real[:4]) or f"{len(sc)} rows")
    check("Every scored forecast had a complete 5-day window after it", "PASS" if bad_win == 0 else "FAIL", f"{bad_win} rows without one")
    live = sc[sc["source"] == "live"]
    check("Live forecasts scored so far", "PASS" if len(live) else "WARN", f"{len(live)} scored (the first arrive after a weekly run)")
else:
    check("Forecast tracking audit", "WARN", "no forecast_scored.csv yet")

# ---------- 5. optional second source ----------
key = os.getenv("FINNHUB_API_KEY")
if key:
    off = []
    for t in sorted(set(px["Ticker"]) - funds):
        try:
            req = urllib.request.Request(f"https://finnhub.io/api/v1/quote?symbol={t}", headers={"X-Finnhub-Token": key})
            q = json.load(urllib.request.urlopen(req, timeout=15))
            mine = px.loc[px["Ticker"] == t, "Close"].iloc[-1]
            if q.get("c") and abs(q["c"] / mine - 1) > 0.005:
                off.append(f"{t}: Finnhub {q['c']} vs ours {mine:.2f}")
        except Exception:                                        # noqa
            off.append(f"{t}: lookup failed")
    check("Latest close vs Finnhub (second source)", "PASS" if not off else "WARN",
          "; ".join(off[:5]) or "all within 0.5% (run after the market has closed)")
else:
    check("Second-source price check", "WARN", "skipped: set FINNHUB_API_KEY to enable")

width = max(len(n) for _, n, _ in rows)
for s, n, d in rows:
    print(f"[{s}] {n.ljust(width)}  {d}")
fails = sum(s == "FAIL" for s, _, _ in rows)
print(f"\n{sum(s == 'PASS' for s, _, _ in rows)} passed, {sum(s == 'WARN' for s, _, _ in rows)} warnings, {fails} failed")
sys.exit(1 if fails else 0)
