"""Position sizing backtest: does sizing by forecast risk beat equal weights?

Run from the project folder (after fetch_stocks.py):
    python position_sizing.py

Compares three portfolios of the stocks in data/stocks.csv (SPY excluded):
  equal_weight      - same weight in every stock
  inv_vol_naive     - weight ~ 1 / (last 20-day volatility)
  inv_vol_forecast  - weight ~ 1 / (blend of HAR-ridge + EWMA forecast)
Forecasts are walk-forward: the model is refit every 21 days using only data
available at that time. Weights are rebalanced every 5 trading days and applied
to the NEXT day's returns (no look-ahead). A 5 basis point cost is charged on
every unit of turnover.
Saves output/charts/position_sizing.png and output/processed/position_sizing_*.csv
Educational only - not trading advice.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HORIZON, EPS = 5, 1e-6
MIN_TRAIN = 750          # ~3 years of history before the first forecast
REFIT_EVERY = 21         # refit the model monthly
REBALANCE_EVERY = 5      # rebalance weekly
COST_BPS = 5             # cost per unit of turnover, in basis points

df = pd.read_csv("data/stocks.csv", parse_dates=["Date"])
ret = (df.pivot(index="Date", columns="Ticker", values="daily_return_pct")
         .sort_index().dropna())
mkt = ret["SPY"]
tickers = [t for t in ret.columns if t not in ("SPY", "QQQ")]   # stocks only, no funds
R = ret[tickers] / 100.0
lv = lambda x: np.log(x + EPS)
feats = ["lv1", "lv5", "lv20", "lv60", "mkt_lv20"]
n = len(ret)
if n < MIN_TRAIN + 300:
    raise SystemExit(f"Need more history: only {n} days. Fetch period='10y'.")


def forecast_series(t):
    """Walk-forward blended volatility forecast for one ticker."""
    r = ret[t]
    X = pd.DataFrame({
        "lv1": lv(r.abs()), "lv5": lv(r.rolling(5).std()),
        "lv20": lv(r.rolling(20).std()), "lv60": lv(r.rolling(60).std()),
        "mkt_lv20": lv(mkt.rolling(20).std()),
    })
    y = r.rolling(HORIZON).std().shift(-HORIZON)
    ewma = np.sqrt((r ** 2).ewm(alpha=0.06, adjust=False).mean())
    out = pd.Series(np.nan, index=ret.index)
    for k in range(MIN_TRAIN, n, REFIT_EVERY):
        # target at row i needs returns up to i+5, so only rows i <= k-5 are known
        train = X.iloc[:k - HORIZON + 1].assign(y=y.iloc[:k - HORIZON + 1]).dropna()
        m = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        m.fit(train[feats], lv(train["y"]))
        resid = lv(train["y"]) - m.predict(train[feats])
        blk = X.iloc[k:k + REFIT_EVERY]
        ok = blk.dropna()
        har = np.exp(m.predict(ok[feats]) + 0.5 * resid.var())
        out.loc[ok.index] = 0.5 * har + 0.5 * ewma.loc[ok.index].values
    return out


print("Building walk-forward forecasts (takes a minute)...")
F = pd.DataFrame({t: forecast_series(t) for t in tickers}).dropna()
N20 = R.mul(100).rolling(20).std().loc[F.index].div(1.0)   # naive vol, % units
N20 = N20.replace(0, np.nan).ffill()

dates = F.index
Rt = R.loc[dates]


def weights_from_vol(V):
    w = 1.0 / V
    return w.div(w.sum(axis=1), axis=0)


W = {
    "equal_weight": pd.DataFrame(1.0 / len(tickers), index=dates, columns=tickers),
    "inv_vol_naive": weights_from_vol(N20),
    "inv_vol_forecast": weights_from_vol(F),
}

rows, equity, dd, daily = [], {}, {}, {}
for name, w in W.items():
    w_reb = w.iloc[::REBALANCE_EVERY].reindex(dates).ffill()
    w_use = w_reb.shift(1).dropna()            # decided yesterday, earned today
    turnover = w_use.diff().abs().sum(axis=1).fillna(0)
    pr = (w_use * Rt.loc[w_use.index]).sum(axis=1) - turnover * COST_BPS / 1e4
    eq = (1 + pr).cumprod()
    peak = eq.cummax()
    yrs = len(pr) / 252
    rows.append({
        "strategy": name,
        "cagr_pct": round((eq.iloc[-1] ** (1 / yrs) - 1) * 100, 1),
        "volatility_pct": round(pr.std() * np.sqrt(252) * 100, 1),
        "sharpe": round(pr.mean() / pr.std() * np.sqrt(252), 2),
        "max_drawdown_pct": round(((eq / peak) - 1).min() * 100, 1),
        "worst_day_pct": round(pr.min() * 100, 1),
        "avg_annual_turnover": round(turnover.sum() / yrs, 1),
        "growth_of_1": round(eq.iloc[-1], 2),
    })
    equity[name], dd[name], daily[name] = eq, eq / peak - 1, pr

res = pd.DataFrame(rows)
print(f"\nBacktest {dates[0].date()} to {dates[-1].date()} "
      f"({len(dates)} days, {len(tickers)} stocks, {COST_BPS} bp cost)")
print(res.to_string(index=False))

latest = pd.DataFrame({
    "equal_weight_pct": (W["equal_weight"].iloc[-1] * 100).round(1),
    "forecast_sized_pct": (W["inv_vol_forecast"].iloc[-1] * 100).round(1),
    "forecast_vol_ann_pct": (F.iloc[-1] * np.sqrt(252)).round(1),
}).sort_values("forecast_sized_pct", ascending=False)
print(f"\nCurrent forecast-sized weights (as of {dates[-1].date()}):")
print(latest.to_string())

os.makedirs("output/charts", exist_ok=True)
os.makedirs("output/processed", exist_ok=True)
res.to_csv("output/processed/position_sizing_results.csv", index=False)
pd.DataFrame(equity).round(5).to_csv("output/processed/position_sizing_equity.csv", index_label="Date")
latest.to_csv("output/processed/position_sizing_weights.csv")

colors = {"equal_weight": "#9aa5b1", "inv_vol_naive": "#f59e0b",
          "inv_vol_forecast": "#2563eb"}
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2]})
for k, eq in equity.items():
    a1.plot(eq.index, eq.values, label=k, color=colors[k], lw=1.6)
a1.set_ylabel("Growth of $1")
a1.set_title("Position sizing backtest (after costs)")
a1.legend(loc="upper left")
a1.grid(alpha=0.3)
for k, d in dd.items():
    a2.plot(d.index, d.values * 100, color=colors[k], lw=1.2)
a2.set_ylabel("Drawdown (%)")
a2.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("output/charts/position_sizing.png", dpi=150)
print("\nSaved output/charts/position_sizing.png")
