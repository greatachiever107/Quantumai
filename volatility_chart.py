"""Weekly volatility forecast chart + risk table (uses the ENSEMBLE model).

Run from the project folder (after fetch_stocks.py; ideally also
build_events.py and fetch_earnings.py):
    python volatility_chart.py
Trains the pooled ridge + gradient-boosting models on ALL history, averages
them with the EWMA estimate (the ensemble that won the backtest in
model_volatility_v3.py), and forecasts volatility for the next 5 trading days.
Stocks with earnings due inside that window are marked with a star.
Saves output/charts/volatility_forecast.png and
output/processed/volatility_forecast.csv.
Educational only - not trading advice.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import volfeatures as vf

ANN, lv = np.sqrt(252), vf.lv
panel, OLD, NEW, tickers = vf.build_panel()
lab = panel.dropna(subset=["y"])
last = panel["Date"].max()
latest = panel[panel["Date"] == last].set_index("Ticker").loc[tickers]


def fit_predict(model, Xtr, ytr, Xte):
    model.fit(Xtr, lv(ytr))
    scale = float(np.mean(ytr / np.exp(model.predict(Xtr))))
    return np.exp(model.predict(Xte)) * scale


ridge = fit_predict(make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
                    lab[NEW], lab["y"], latest[NEW])
gbm = fit_predict(HistGradientBoostingRegressor(
    max_depth=3, learning_rate=0.05, max_iter=250, min_samples_leaf=100,
    l2_regularization=1.0, random_state=0), lab[NEW], lab["y"], latest[NEW])
ens = (latest["ewma"].values + ridge + gbm) / 3

out = pd.DataFrame({
    "Ticker": tickers,
    "recent_20d_vol_ann_pct": (latest["naive"].values * ANN).round(1),
    "forecast_5d_vol_ann_pct": (ens * ANN).round(1),
    "forecast_vs_recent_pct": ((ens / latest["naive"].values - 1) * 100).round(1),
    "typical_daily_move_pct": ens.round(2),
})
if "earn_next5" in latest.columns:
    out["earnings_in_window"] = (latest["earn_next5"].values > 0)
    if os.path.exists("events/earnings.csv"):
        er = pd.read_csv("events/earnings.csv", parse_dates=["date"])
        nxt = er[er["date"] > last].groupby("Ticker")["date"].min()
        out["next_earnings"] = out["Ticker"].map(nxt).dt.date
else:
    out["earnings_in_window"] = False
out = out.sort_values("forecast_5d_vol_ann_pct")

print(f"\nForecast as of {last.date()} (next {vf.HORIZON} trading days), ensemble model")
print(out.to_string(index=False))

os.makedirs("output/charts", exist_ok=True)
os.makedirs("output/processed", exist_ok=True)
out.to_csv("output/processed/volatility_forecast.csv", index=False)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 6), sharey=True,
                             gridspec_kw={"width_ratios": [3, 2]})
y = np.arange(len(out))
h = 0.38
a1.barh(y + h / 2, out["recent_20d_vol_ann_pct"], h, label="Recent (last 20 days)",
        color="#9aa5b1")
a1.barh(y - h / 2, out["forecast_5d_vol_ann_pct"], h, label="Forecast (next 5 days)",
        color="#2563eb")
a1.set_yticks(y)
a1.set_yticklabels([t + ("  \u2605 earnings" if e else "")
                    for t, e in zip(out["Ticker"], out["earnings_in_window"])])
a1.set_xlabel("Annualized volatility (%)")
a1.set_title("Volatility: recent vs forecast")
a1.legend(loc="lower right")
a1.grid(axis="x", alpha=0.3)

chg = out["forecast_vs_recent_pct"]
a2.barh(y, chg, color="#2563eb")
a2.axvline(0, color="black", lw=0.8)
a2.set_xlabel("Forecast vs recent (%)")
a2.set_title("Expected change in risk\n(right = rising, left = falling)")
a2.grid(axis="x", alpha=0.3)

fig.suptitle(f"US stocks - volatility forecast as of {last.date()}  "
             "(\u2605 = earnings due in the window)", fontsize=13)
fig.tight_layout()
fig.savefig("output/charts/volatility_forecast.png", dpi=150)
print("\nSaved output/charts/volatility_forecast.png")
print("Saved output/processed/volatility_forecast.csv")
