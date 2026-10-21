"""Volatility forecast v3: pooled (panel) models with richer features.

Run from the project folder (after fetch_stocks.py, 10y data):
    python model_volatility_v3.py                 # everything on
    python model_volatility_v3.py --no-events     # no FOMC/NFP features
    python model_volatility_v3.py --no-earnings   # no earnings features

Features (built in volfeatures.py): range-based volatility, overnight gaps,
long-run level, market (SPY) stress, scheduled macro events in the next 5 days
(events/events.csv) and per-stock earnings in the next 5 days / last 5 / last
20 days (events/earnings.csv). One pooled model learns from all stocks.
Walk-forward testing with a 5-day gap. Lower MAE / QLIKE is better.
Educational only - not trading advice.
"""
import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import volfeatures as vf

HORIZON, lv = vf.HORIZON, vf.lv
panel, OLD, NEW, tickers = vf.build_panel(
    use_events="--no-events" not in sys.argv,
    use_earnings="--no-earnings" not in sys.argv)
lab = panel.dropna(subset=["y"]).reset_index(drop=True)
print("Features used:", len(NEW), "->", ", ".join(c for c in NEW if c not in vf.BASE) or "base only")


def fit_predict(model, Xtr, ytr, Xte):
    model.fit(Xtr, lv(ytr))
    p_tr = model.predict(Xtr)
    scale = float(np.mean(ytr / np.exp(p_tr)))     # Jensen correction from TRAIN only
    return np.exp(model.predict(Xte)) * scale


dates = np.array(sorted(lab["Date"].unique()))
tscv = TimeSeriesSplit(n_splits=5, gap=HORIZON)
methods = ["naive_vol20", "ewma", "har_v2_per_stock", "panel_ridge", "panel_gbm", "ensemble"]
meta = []
for fold, (tr_d, te_d) in enumerate(tscv.split(dates), 1):
    tr = lab[lab["Date"].isin(dates[tr_d])]
    te = lab[lab["Date"].isin(dates[te_d])].copy()
    te["fold"] = fold

    pr = fit_predict(make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
                     tr[NEW], tr["y"], te[NEW])
    gb = fit_predict(HistGradientBoostingRegressor(
        max_depth=3, learning_rate=0.05, max_iter=250, min_samples_leaf=100,
        l2_regularization=1.0, random_state=0),
        tr[NEW], tr["y"], te[NEW])

    # v2 baseline: one small ridge model per stock (the previous best)
    har = pd.Series(np.nan, index=te.index)
    for t in tickers:
        a, b = tr[tr["Ticker"] == t], te[te["Ticker"] == t]
        if len(a) and len(b):
            har.loc[b.index] = fit_predict(make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
                                           a[OLD], a["y"], b[OLD])
    te["naive_vol20"] = te["naive"]
    te["har_v2_per_stock"] = 0.5 * har + 0.5 * te["ewma"]   # v2 "blend"
    te["panel_ridge"], te["panel_gbm"] = pr, gb
    te["ensemble"] = (te["ewma"] + pr + gb) / 3
    meta.append(te)

res = pd.concat(meta)


def qlike(y, f):
    ratio = (y / f) ** 2
    return ratio - np.log(ratio) - 1


mae = res.groupby("Ticker").apply(
    lambda g: pd.Series({m: np.mean(np.abs(g[m] - g["y"])) for m in methods}),
    include_groups=False).round(3)
print("\n=== MAE by stock, next-5-day volatility (lower is better) ===")
print(mae.to_string())

summary = pd.DataFrame({
    "avg_MAE": [mae[m].mean() for m in methods],
    "avg_QLIKE": [qlike(res["y"], res[m]).mean() for m in methods],
    "stocks_beating_naive": [(mae[m] < mae["naive_vol20"]).sum() for m in methods],
    "stocks_beating_v2": [(mae[m] < mae["har_v2_per_stock"]).sum() for m in methods],
}, index=methods).round(3)
summary["MAE_vs_naive_%"] = ((summary["avg_MAE"] / summary.loc["naive_vol20", "avg_MAE"] - 1)
                             * 100).round(1)
print(f"\n=== Summary over {res['Ticker'].nunique()} stocks ===")
print(summary.to_string())

fold_mae = res.groupby("fold").apply(
    lambda g: pd.Series({m: np.mean(np.abs(g[m] - g["y"])) for m in
                         ["naive_vol20", "har_v2_per_stock", "ensemble"]}),
    include_groups=False).round(3)
fold_mae["ensemble_beats_naive"] = fold_mae["ensemble"] < fold_mae["naive_vol20"]
print("\n=== Consistency across time periods (5 walk-forward folds) ===")
print(fold_mae.to_string())

# Accuracy around earnings: the window where a model without earnings info should struggle
if "earn_next5" in res.columns:
    flag = res["earn_next5"] > 0
    if flag.sum() > 30:
        print("\n=== MAE when earnings fall inside the forecast window vs not ===")
        rows = []
        for name, m in [("earnings in next 5 days", flag), ("no earnings in window", ~flag)]:
            g = res[m]
            rows.append({"rows": len(g), "window": name,
                         **{k: round(float(np.mean(np.abs(g[k] - g["y"]))), 3)
                            for k in ["naive_vol20", "har_v2_per_stock", "ensemble"]}})
        print(pd.DataFrame(rows).to_string(index=False))

os.makedirs("output/processed", exist_ok=True)
mae.to_csv("output/processed/model_volatility_v3_by_stock.csv")
summary.to_csv("output/processed/model_volatility_v3_summary.csv")
print("\nSaved output/processed/model_volatility_v3_*.csv")
