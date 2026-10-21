"""Forecast tracking: log each forecast, then score it once its 5 days are over.

    python track_forecasts.py                # log the latest forecast + score all
    python track_forecasts.py --backfill 26  # also rebuild the last 26 weekly
                                             # forecasts using only data available then
Run after volatility_chart.py. Results: output/tracking/*.csv
  source "live"     = forecast saved on the day, then scored on what happened
  source "backfill" = rebuilt after the fact with strictly past data (honest, but
                      not a live record - treat "live" as the real test)
"""
import os, sys, tempfile
import numpy as np
import pandas as pd
import volfeatures as vf

H, LOG, MIN_POS = 5, "output/tracking/forecast_log.csv", 800
os.makedirs("output/tracking", exist_ok=True)
df = pd.read_csv("data/stocks.csv", parse_dates=["Date"])
ret = df.pivot(index="Date", columns="Ticker", values="daily_return_pct").sort_index().dropna()
cols = ["as_of", "Ticker", "forecast_daily_vol", "recent_daily_vol", "earnings_in_window", "source"]
log = pd.read_csv(LOG, parse_dates=["as_of"]) if os.path.exists(LOG) else pd.DataFrame(columns=cols)
log["as_of"] = pd.to_datetime(log["as_of"])
have = set(log["as_of"].dt.normalize())
new = []

# 1) log the latest live forecast
fc = "output/processed/volatility_forecast.csv"
as_of = ret.index[-1]
if not os.path.exists(fc):
    print("No volatility_forecast.csv - run volatility_chart.py first.")
elif os.path.getmtime(fc) < os.path.getmtime("data/stocks.csv") - 5:
    print("Forecast file is older than the price data - rerun volatility_chart.py, then this.")
elif as_of in have:
    print(f"Forecast for {as_of.date()} already logged.")
else:
    f = pd.read_csv(fc)
    for _, r in f.iterrows():
        new.append([as_of, r["Ticker"], r["typical_daily_move_pct"],
                    ret[r["Ticker"]].tail(20).std(), bool(r.get("earnings_in_window", False)), "live"])
    print(f"Logged live forecast for {as_of.date()} ({len(f)} stocks).")

# 2) optional backfill: rebuild past weekly forecasts with only the data available then
if "--backfill" in sys.argv:
    n = int(sys.argv[sys.argv.index("--backfill") + 1])
    done = 0
    for k in range(1, n + 1):
        pos = len(ret) - 1 - H * k
        if pos < MIN_POS:
            break
        d = ret.index[pos]
        if d in have:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "s.csv")
            df[df["Date"] <= d].to_csv(p, index=False)
            panel, _, feats, _ = vf.build_panel(verbose=False, data_path=p)
        out, last = vf.ensemble_forecast(panel, feats)
        for t, r in out.iterrows():
            new.append([last, t, r["forecast_daily_vol"], r["recent_daily_vol"],
                        bool(r["earnings_in_window"]), "backfill"])
        done += 1
        print(f"  backfilled {last.date()} ({done}/{n})", flush=True)

if new:
    log = pd.concat([log, pd.DataFrame(new, columns=cols)], ignore_index=True)
log = log.sort_values(["as_of", "Ticker"]).reset_index(drop=True)
log.to_csv(LOG, index=False)

# 3) score every forecast whose 5-day window has finished
rows = []
for _, r in log.iterrows():
    if r["as_of"] not in ret.index:
        continue
    pos = ret.index.get_loc(r["as_of"])
    if pos + H >= len(ret):
        continue
    real = ret[r["Ticker"]].iloc[pos + 1:pos + 1 + H].std()
    rows.append({**r.to_dict(), "realized_daily_vol": real,
                 "ens_err": abs(r["forecast_daily_vol"] - real),
                 "naive_err": abs(r["recent_daily_vol"] - real),
                 "change_called_pct": (r["forecast_daily_vol"] / r["recent_daily_vol"] - 1) * 100,
                 "change_actual_pct": (real / r["recent_daily_vol"] - 1) * 100})
sc = pd.DataFrame(rows)
if sc.empty:
    print(f"\nNothing to score yet - {len(log[log.as_of == log.as_of.max()])} forecast(s) logged. "
          "Run again next week (or use --backfill 26).")
    sys.exit()
sc["closer_than_naive"] = sc["ens_err"] < sc["naive_err"]
sc["direction_correct"] = np.sign(sc["change_called_pct"]) == np.sign(sc["change_actual_pct"])
sc["big_call"] = sc["change_called_pct"].abs() >= 10
sc.to_csv("output/tracking/forecast_scored.csv", index=False)

def summ(g, name):
    b = g[g["big_call"]]
    return {"source": name, "forecasts": len(g), "weeks": g["as_of"].nunique(),
            "ens_mae": round(g["ens_err"].mean(), 3), "naive_mae": round(g["naive_err"].mean(), 3),
            "closer_than_naive_pct": round(g["closer_than_naive"].mean() * 100, 1),
            "direction_hit_pct": round(g["direction_correct"].mean() * 100, 1),
            "big_calls": len(b),
            "big_call_hit_pct": round(b["direction_correct"].mean() * 100, 1) if len(b) else None}

s = pd.DataFrame([summ(sc[sc.source == k], k) for k in ["live", "backfill"] if (sc.source == k).any()]
                 + [summ(sc, "all")])
s.to_csv("output/tracking/tracking_summary.csv", index=False)
print("\n=== Forecast tracking: ensemble vs naive on what actually happened ===")
print(s.to_string(index=False))
print("\nBy stock (all scored forecasts):")
print(sc.groupby("Ticker").agg(n=("ens_err", "size"), ens_mae=("ens_err", "mean"),
      naive_mae=("naive_err", "mean"), closer_pct=("closer_than_naive", lambda x: x.mean() * 100)
      ).round(2).to_string())
print("\nSaved output/tracking/forecast_log.csv, forecast_scored.csv, tracking_summary.csv")
