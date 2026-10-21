"""Download US stock prices one ticker at a time, with retries, and save
them to data/stocks.csv.

Run from the project folder:
    python fetch_stocks.py
Needs:  pip install yfinance

Why one at a time: downloading all tickers at once can make Yahoo reject some
of them (the "possibly delisted" message is usually a temporary block, not a
real delisting). Each successful ticker is saved in cache_prices/, so if some
fail you can simply run the script again and it only fetches the missing ones.
"""
import os
import time
import pandas as pd
import yfinance as yf

PERIOD = "10y"
RETRIES = 4
CACHE = "cache_prices"      # outside data/ so main.py run does not analyse it

sectors = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "AMZN": "Consumer", "TSLA": "Consumer", "WMT": "Consumer",
    "JPM": "Financials", "V": "Financials",
    "XOM": "Energy", "JNJ": "Healthcare",
    "SPY": "Market benchmark",
}

os.makedirs(CACHE, exist_ok=True)
os.makedirs("data", exist_ok=True)


def fetch(ticker):
    path = os.path.join(CACHE, f"{ticker}.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    for attempt in range(1, RETRIES + 1):
        try:
            d = yf.Ticker(ticker).history(period=PERIOD, auto_adjust=True)
            if d is not None and len(d) > 200:
                d = d.reset_index()[["Date", "Open", "High", "Low",
                                     "Close", "Volume"]]
                d["Date"] = pd.to_datetime(d["Date"]).dt.tz_localize(None).dt.date
                d.to_csv(path, index=False)
                return d
        except Exception as e:
            print(f"  {ticker}: attempt {attempt} error: {e}")
        wait = 3 * attempt
        print(f"  {ticker}: attempt {attempt} failed, waiting {wait}s")
        time.sleep(wait)
    return None


frames, missing = [], []
for t, sector in sectors.items():
    print(f"Fetching {t} ...")
    d = fetch(t)
    if d is None:
        missing.append(t)
        continue
    d = d.copy()
    d["Ticker"] = t
    d["Sector"] = sector
    d["daily_return_pct"] = d["Close"].pct_change() * 100
    frames.append(d)
    time.sleep(1)           # be polite to the server

if frames:
    out = pd.concat(frames)
    out = out.dropna(subset=["Close", "daily_return_pct"])
    out.to_csv("data/stocks.csv", index=False)
    print(f"\nSaved data/stocks.csv with {len(out)} rows "
          f"({out['Ticker'].nunique()} tickers)")
if missing:
    print(f"STILL MISSING: {missing}  -> wait a few minutes and run again.")
else:
    print("All tickers downloaded.")
