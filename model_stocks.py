"""Mathematical and machine-learning models on data/stocks.csv.

Run from the project folder (after fetch_stocks.py):
    python model_stocks.py
Needs:  pip install scikit-learn
Results are printed and saved to output/processed/.
Descriptive/educational only - not trading advice.
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("data/stocks.csv", parse_dates=["Date"])
ret = (df.pivot(index="Date", columns="Ticker", values="daily_return_pct")
         .sort_index().dropna())
mkt = ret["SPY"]
tickers = [t for t in ret.columns if t != "SPY"]
tscv = TimeSeriesSplit(n_splits=5)   # always train on the past, test on the future

# ---- MODEL 1: market model (beta). A mathematical model, no prediction ----
rows = []
for t in tickers:
    beta, alpha = np.polyfit(mkt, ret[t], 1)
    rows.append({
        "Ticker": t,
        "beta": round(beta, 2),
        "alpha_annual_pct": round(alpha * 252, 1),
        "r_squared": round(np.corrcoef(mkt, ret[t])[0, 1] ** 2, 2),
        "volatility_annual_pct": round(ret[t].std() * np.sqrt(252), 1),
    })
beta_df = pd.DataFrame(rows)
print("\n=== MODEL 1: market model (return = alpha + beta * SPY return) ===")
print(beta_df.to_string(index=False))

# ---- MODEL 2: next-day direction (up/down) with ML ----
def direction_data(t):
    r = ret[t]
    X = pd.DataFrame({f"lag{k}": r.shift(k) for k in range(1, 6)})
    X["vol5"] = r.rolling(5).std().shift(1)
    X["vol20"] = r.rolling(20).std().shift(1)
    X["spy_lag1"] = mkt.shift(1)
    d = X.join((r > 0).astype(int).rename("y")).dropna()
    return d.drop(columns="y"), d["y"]

models = {
    "logistic": make_pipeline(StandardScaler(), LogisticRegression()),
    "random_forest": RandomForestClassifier(n_estimators=200, max_depth=4,
                                            random_state=0),
}
rows = []
for t in tickers:
    X, y = direction_data(t)
    res = {"Ticker": t}
    base, scores = [], {n: [] for n in models}
    for tr, te in tscv.split(X):
        majority = int(y.iloc[tr].mean() >= 0.5)
        base.append((y.iloc[te] == majority).mean())
        for n, m in models.items():
            m.fit(X.iloc[tr], y.iloc[tr])
            scores[n].append(m.score(X.iloc[te], y.iloc[te]))
    res["baseline_acc"] = round(np.mean(base), 3)
    for n in models:
        res[n + "_acc"] = round(np.mean(scores[n]), 3)
    rows.append(res)
dir_df = pd.DataFrame(rows)
print("\n=== MODEL 2: predict next-day direction (walk-forward accuracy) ===")
print(dir_df.to_string(index=False))

# ---- MODEL 3: forecast next-5-day volatility ----
rows = []
for t in tickers:
    r = ret[t]
    X = pd.DataFrame({"vol5": r.rolling(5).std(),
                      "vol20": r.rolling(20).std(),
                      "vol60": r.rolling(60).std()})
    y = r.rolling(5).std().shift(-5).rename("y")   # std of the next 5 days
    d = X.join(y).dropna()
    X, y = d[["vol5", "vol20", "vol60"]], d["y"]
    mae_model, mae_naive = [], []
    for tr, te in tscv.split(X):
        m = LinearRegression().fit(X.iloc[tr], y.iloc[tr])
        mae_model.append(np.mean(np.abs(m.predict(X.iloc[te]) - y.iloc[te])))
        mae_naive.append(np.mean(np.abs(X["vol20"].iloc[te] - y.iloc[te])))
    rows.append({"Ticker": t,
                 "naive_mae": round(np.mean(mae_naive), 3),
                 "model_mae": round(np.mean(mae_model), 3)})
vol_df = pd.DataFrame(rows)
print("\n=== MODEL 3: forecast next-5-day volatility (lower MAE is better) ===")
print(vol_df.to_string(index=False))

os.makedirs("output/processed", exist_ok=True)
beta_df.to_csv("output/processed/model_beta.csv", index=False)
dir_df.to_csv("output/processed/model_direction.csv", index=False)
vol_df.to_csv("output/processed/model_volatility.csv", index=False)
print("\nSaved results to output/processed/")
