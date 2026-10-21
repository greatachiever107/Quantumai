"""Safety check before publishing: refuse to commit a broken or stale snapshot.

    python check_snapshot.py        # exit code 0 = fine, 1 = problem
Used by the weekly GitHub Action so a failed Yahoo download can never overwrite
the last good data on the live site.
"""
import sys
import pandas as pd

problems = []
try:
    px = pd.read_csv("snapshot/data/stocks.csv", usecols=["Date", "Ticker"], parse_dates=["Date"])
    n = px["Ticker"].nunique()
    if n < 11:
        problems.append(f"only {n} tickers in stocks.csv (expected 11 incl. SPY)")
    age = (pd.Timestamp.now(tz="UTC").tz_localize(None).normalize() - px["Date"].max()).days
    if age > 6:
        problems.append(f"latest price date {px['Date'].max().date()} is {age} days old")
    fc = pd.read_csv("snapshot/output/processed/volatility_forecast.csv")
    if len(fc) < 10:
        problems.append(f"forecast has only {len(fc)} stocks (expected 10)")
    er = pd.read_csv("snapshot/events/earnings.csv")
    if er["Ticker"].nunique() < 10:
        problems.append(f"earnings dates found for only {er['Ticker'].nunique()} stocks")
    pd.read_csv("snapshot/output/tracking/tracking_summary.csv")
except Exception as e:
    problems.append(f"could not read snapshot files: {e}")

if problems:
    print("SNAPSHOT CHECK FAILED - nothing will be published:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print(f"Snapshot OK: {n} tickers, latest price {px['Date'].max().date()}, {len(fc)} forecasts.")
