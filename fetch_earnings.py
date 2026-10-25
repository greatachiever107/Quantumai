"""Download each stock's earnings dates and save events/earnings.csv.

Run from the project folder (after fetch_stocks.py):
    python fetch_earnings.py
Needs yfinance (already installed). One ticker at a time, with retries; each
success is cached in cache_earnings/ so a rerun only fetches what is missing.

Output columns:
  date               announcement date (US Eastern)
  Ticker
  timing             BMO = before market open (reaction that same day)
                     AMC = after market close (reaction next trading day)
                     UNK = time not given by Yahoo
  eps_surprise_pct   (reported EPS - estimate) / estimate, in %; blank if not out yet
  reported           True once the results are out (False = upcoming date)
"""
import os
import time
import pandas as pd
import yfinance as yf

LIMIT = 60            # up to 60 past+future announcements (~15 years)
RETRIES = 4
CACHE = "cache_earnings"
os.makedirs(CACHE, exist_ok=True)
os.makedirs("events", exist_ok=True)

tickers = sorted(t for t in pd.read_csv("data/stocks.csv", usecols=["Ticker"])["Ticker"].unique()
                 if t not in ("SPY", "QQQ"))   # funds have no earnings


def tidy(raw, ticker):
    d = raw.copy()
    idx = pd.DatetimeIndex(d.index)
    if idx.tz is not None:
        idx = idx.tz_convert("America/New_York")
    hour = idx.hour
    timing = pd.Series(
        ["UNK" if (h == 0 and m == 0) else ("BMO" if h < 16 else "AMC")
         for h, m in zip(idx.hour, idx.minute)])
    sur = d["Surprise(%)"] if "Surprise(%)" in d.columns else pd.Series(float("nan"), index=d.index)
    rep = d["Reported EPS"] if "Reported EPS" in d.columns else pd.Series(float("nan"), index=d.index)
    out = pd.DataFrame({
        "date": idx.tz_localize(None).normalize() if idx.tz is not None else idx.normalize(),
        "Ticker": ticker,
        "timing": timing.values,
        "eps_surprise_pct": pd.to_numeric(sur.values, errors="coerce"),
        "reported": pd.Series(rep.values).notna().values,
    })
    return out.drop_duplicates(subset=["date"]).sort_values("date")


def fetch(ticker):
    path = os.path.join(CACHE, f"{ticker}.csv")
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["date"])
    for attempt in range(1, RETRIES + 1):
        try:
            tk = yf.Ticker(ticker)
            try:
                raw = tk.get_earnings_dates(limit=LIMIT)
            except AttributeError:
                raw = tk.earnings_dates
            if raw is not None and len(raw) >= 4:
                d = tidy(raw, ticker)
                d.to_csv(path, index=False)
                return d
        except Exception as e:
            print(f"  {ticker}: attempt {attempt} error: {e}")
        wait = 3 * attempt
        print(f"  {ticker}: attempt {attempt} failed, waiting {wait}s")
        time.sleep(wait)
    return None


frames, missing = [], []
for t in tickers:
    print(f"Fetching earnings dates for {t} ...")
    d = fetch(t)
    if d is None:
        missing.append(t)
    else:
        frames.append(d)
    time.sleep(1)

if frames:
    out = pd.concat(frames).sort_values(["date", "Ticker"])
    out.to_csv("events/earnings.csv", index=False)
    print("\nCoverage (announcements found per stock):")
    cov = out.groupby("Ticker").agg(n=("date", "size"), first=("date", "min"),
                                    last=("date", "max"),
                                    unknown_timing=("timing", lambda s: (s == "UNK").sum()))
    print(cov.to_string())
    print(f"\nSaved events/earnings.csv ({len(out)} rows)")
if missing:
    print(f"STILL MISSING: {missing} -> wait a few minutes and run again.")
