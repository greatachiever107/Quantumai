"""Improved volatility forecast (Model 3, version 2).

Run from the project folder (after fetch_stocks.py):
    python model_volatility.py
Predicts the std of daily returns over the NEXT 5 trading days, and compares
four approaches with walk-forward testing (train on past, test on future):
  naive_vol20  - "next week looks like the last 20 days"
  ewma         - exponentially weighted volatility (RiskMetrics, lambda 0.94)
  har_ridge    - HAR-style model: ridge regression on LOG volatilities
                 (1, 5, 20, 60-day) + market volatility
  blend        - simple average of ewma and har_ridge
Lower MAE is better. Educational only - not trading advice.
"""
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HORIZON = 5
EPS = 1e-6

df = pd.read_csv("data/stocks.csv", parse_dates=["Date"])
ret = (df.pivot(index="Date", columns="Ticker", values="daily_return_pct")
         .sort_index().dropna())
mkt = ret["SPY"]
tickers = [t for t in ret.columns if t != "SPY"]

# gap=HORIZON stops training rows whose 5-day target overlaps the test period
tscv = TimeSeriesSplit(n_splits=5, gap=HORIZON)


def lv(x):
    return np.log(x + EPS)


def features(r):
    X = pd.DataFrame({
        "lv1": lv(r.abs()),                       # yesterday's move
        "lv5": lv(r.rolling(5).std()),
        "lv20": lv(r.rolling(20).std()),
        "lv60": lv(r.rolling(60).std()),
        "mkt_lv20": lv(mkt.rolling(20).std()),    # overall market stress
    })
    return X


rows = []
for t in tickers:
    r = ret[t]
    X = features(r)
    ewma = np.sqrt((r ** 2).ewm(alpha=0.06, adjust=False).mean())  # lambda 0.94
    y = r.rolling(HORIZON).std().shift(-HORIZON)                   # future vol
    d = X.assign(ewma=ewma, naive=r.rolling(20).std(), y=y).dropna()
    feats = ["lv1", "lv5", "lv20", "lv60", "mkt_lv20"]

    res = {k: [] for k in ["naive_vol20", "ewma", "har_ridge", "blend"]}
    for tr, te in tscv.split(d):
        trn, tst = d.iloc[tr], d.iloc[te]
        m = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        m.fit(trn[feats], lv(trn["y"]))
        # exp() of a log-forecast is slightly low (Jensen); correct with
        # the average residual size seen in TRAINING data only
        resid = lv(trn["y"]) - m.predict(trn[feats])
        har = np.exp(m.predict(tst[feats]) + 0.5 * resid.var())
        preds = {
            "naive_vol20": tst["naive"].values,
            "ewma": tst["ewma"].values,
            "har_ridge": har,
        }
        preds["blend"] = 0.5 * preds["ewma"] + 0.5 * preds["har_ridge"]
        for k, p in preds.items():
            res[k].append(np.mean(np.abs(p - tst["y"].values)))

    row = {"Ticker": t}
    row.update({k + "_mae": round(float(np.mean(v)), 3) for k, v in res.items()})
    best = min(res, key=lambda k: np.mean(res[k]))
    row["best"] = best
    rows.append(row)

out = pd.DataFrame(rows)
print("\n=== Volatility forecast, next 5 days (MAE, lower is better) ===")
print(out.to_string(index=False))

cols = [c for c in out.columns if c.endswith("_mae")]
print("\nAverage MAE across stocks:")
print(out[cols].mean().round(3).to_string())
wins = (out[cols].sub(out["naive_vol20_mae"], axis=0) < 0).sum()
print("\nStocks where each method beats the naive baseline "
      f"(out of {len(out)}):")
print(wins.drop("naive_vol20_mae").to_string())

os.makedirs("output/processed", exist_ok=True)
out.to_csv("output/processed/model_volatility_v2.csv", index=False)
print("\nSaved output/processed/model_volatility_v2.csv")
