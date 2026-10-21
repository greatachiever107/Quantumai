"""Shared feature building for the volatility models (used by
model_volatility_v3.py and volatility_chart.py).

build_panel() reads data/stocks.csv (+ optional events/events.csv and
events/earnings.csv) and returns one row per stock per day with features and,
where known, the target y = volatility over the NEXT 5 trading days.
Rows for the latest day have y = NaN: those are the rows you forecast from.
"""
import os
import numpy as np
import pandas as pd

HORIZON, EPS = 5, 1e-6
lv = lambda x: np.log(x + EPS)

OLD = ["lv1", "lv5", "lv20", "lv60", "mkt_lv20"]                       # v2 features
BASE = ["lv1", "lv5", "lv20", "lv60", "lv250", "lvp1", "lvp5", "lvp20", "lvp60",
        "gap5", "ret5z", "ret20z", "mkt_lv5", "mkt_lv20", "mkt_lvp20",
        "mkt_ret5z", "avg_lv20"]
EARN = ["earn_next5", "earn_past5", "earn_past20"]


def build_panel(use_events=True, use_earnings=True, verbose=True,
                data_path="data/stocks.csv"):
    df = pd.read_csv(data_path, parse_dates=["Date"])
    need = {"Open", "High", "Low", "Close", "daily_return_pct", "Ticker"}
    if not need.issubset(df.columns):
        raise SystemExit(f"stocks.csv is missing columns: {need - set(df.columns)}. "
                         "Re-run the latest fetch_stocks.py.")

    def pv(col):
        return df.pivot(index="Date", columns="Ticker", values=col).sort_index()

    ret = pv("daily_return_pct").dropna()
    idx = ret.index
    # calendar extended ~2 weeks so "events in the next 5 days" works on the last row
    idx_ext = idx.append(pd.bdate_range(idx[-1] + pd.Timedelta(days=1), periods=10))
    O, H, L, C = (pv(c).reindex(idx) for c in ["Open", "High", "Low", "Close"])
    park = np.sqrt(np.log(H / L) ** 2 / (4 * np.log(2))) * 100      # range vol, % per day
    gap = np.log(O / C.shift(1)).abs() * 100                        # overnight gap, %
    mkt_r, mkt_p = ret["SPY"], park["SPY"]
    tickers = [t for t in ret.columns if t != "SPY"]
    avg_lv20 = pd.concat([lv(ret[t].rolling(20).std()) for t in tickers], axis=1).mean(axis=1)

    # ---- market-wide scheduled events (FOMC, NFP, anything in extra_events) ----
    EV = {}
    if use_events and os.path.exists("events/events.csv"):
        ev = pd.read_csv("events/events.csv", parse_dates=["date"])
        ev = ev[ev["date"] >= idx_ext[0]]
        pos = idx_ext.searchsorted(ev["date"])
        ev = ev[pos < len(idx_ext)].assign(i=pos[pos < len(idx_ext)])
        groups = {"fomc": ev[ev["event"] == "FOMC"]["i"],
                  "nfp": ev[ev["event"] == "NFP"]["i"],
                  "other": ev[~ev["event"].isin(["FOMC", "NFP"])]["i"]}
        for name, ii in groups.items():
            if len(ii) == 0:
                continue
            ind = pd.Series(0.0, index=idx_ext)
            ind.iloc[ii.values] = 1.0
            EV["ev_" + name + "5"] = ind.rolling(HORIZON).sum().shift(-HORIZON).reindex(idx)

    # ---- per-stock earnings (reaction day = same day BMO, next trading day AMC) ----
    er = None
    if os.path.exists("events/earnings.csv"):
        er = pd.read_csv("events/earnings.csv", parse_dates=["date"])
        er = er[er["Ticker"].isin(tickers) & (er["date"] >= idx_ext[0] - pd.Timedelta(days=5))]
        p = idx_ext.searchsorted(er["date"]) + (er["timing"] == "AMC").astype(int).values
        er = er.assign(i=p)
        er = er[er["i"] < len(idx_ext)]

    frames, uncovered = [], []
    for t in tickers:
        r = ret[t]
        s20 = r.rolling(20).std()
        f = pd.DataFrame({
            "lv1": lv(r.abs()),
            "lv5": lv(r.rolling(5).std()),
            "lv20": lv(s20),
            "lv60": lv(r.rolling(60).std()),
            "lv250": lv(r.rolling(250).std()),
            "lvp1": lv(park[t]),
            "lvp5": lv(park[t].rolling(5).mean()),
            "lvp20": lv(park[t].rolling(20).mean()),
            "lvp60": lv(park[t].rolling(60).mean()),
            "gap5": lv(gap[t].rolling(5).mean()),
            "ret5z": r.rolling(5).sum() / (s20 * np.sqrt(5) + EPS),
            "ret20z": r.rolling(20).sum() / (s20 * np.sqrt(20) + EPS),
            "mkt_lv5": lv(mkt_r.rolling(5).std()),
            "mkt_lv20": lv(mkt_r.rolling(20).std()),
            "mkt_lvp20": lv(mkt_p.rolling(20).mean()),
            "mkt_ret5z": mkt_r.rolling(5).sum() / (mkt_r.rolling(20).std() * np.sqrt(5) + EPS),
            "avg_lv20": avg_lv20,
            "naive": s20,
            "ewma": np.sqrt((r ** 2).ewm(alpha=0.06, adjust=False).mean()),
            "y": r.rolling(HORIZON).std().shift(-HORIZON),
        })
        for k, v in EV.items():
            f[k] = v
        if er is not None:
            e_i = er.loc[er["Ticker"] == t, "i"].values
            if len(e_i):
                s = pd.Series(0.0, index=idx_ext)
                s.iloc[e_i] = 1.0
                f["earn_next5"] = s.rolling(HORIZON).sum().shift(-HORIZON).reindex(idx)
                f["earn_past5"] = s.rolling(5).sum().reindex(idx)
                f["earn_past20"] = s.rolling(20).sum().reindex(idx)
                f.iloc[:min(int(e_i.min()), len(f)), f.columns.get_indexer(EARN)] = np.nan
            else:
                for c in EARN:                       # no earnings data for this stock
                    f[c] = np.nan
                uncovered.append(t)
        f["Ticker"] = t
        frames.append(f.reset_index())

    panel = pd.concat(frames).sort_values(["Date", "Ticker"]).reset_index(drop=True)
    earn_cols = EARN if er is not None else []
    feats = BASE + list(EV) + (earn_cols if use_earnings else [])
    # earnings coverage limits the sample in BOTH modes, so with/without runs compare fairly
    panel = panel.dropna(subset=BASE + list(EV) + earn_cols + ["naive", "ewma"])
    panel = panel.reset_index(drop=True)

    if verbose:
        print("Market event features:", ", ".join(EV) if EV else "off")
        if er is None:
            print("Earnings features: off (no events/earnings.csv - run fetch_earnings.py)")
        else:
            print("Earnings features:", "ON" if use_earnings else "OFF (sample still limited "
                  "to dates with earnings coverage)")
            if uncovered:
                print("  no earnings data for:", ", ".join(uncovered), "(dropped)")
        lab = panel["y"].notna().sum()
        print(f"Panel: {len(panel)} rows ({lab} labelled), "
              f"{panel['Ticker'].nunique()} stocks, "
              f"{panel['Date'].min().date()} to {panel['Date'].max().date()}")
    return panel, OLD, feats, tickers


def ensemble_forecast(panel, feats):
    """Fit the pooled ridge + gradient-boosting models on all labelled rows and
    return the ensemble forecast (daily vol, %) for the latest date, per stock."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    lab = panel.dropna(subset=["y"])
    last = panel["Date"].max()
    latest = panel[panel["Date"] == last].set_index("Ticker")

    def fp(model):
        model.fit(lab[feats], lv(lab["y"]))
        scale = float(np.mean(lab["y"] / np.exp(model.predict(lab[feats]))))
        return np.exp(model.predict(latest[feats])) * scale

    ridge = fp(make_pipeline(StandardScaler(), Ridge(alpha=10.0)))
    gbm = fp(HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=250,
                                           min_samples_leaf=100, l2_regularization=1.0,
                                           random_state=0))
    out = pd.DataFrame({"forecast_daily_vol": (latest["ewma"].values + ridge + gbm) / 3,
                        "recent_daily_vol": latest["naive"].values,
                        "earnings_in_window": (latest["earn_next5"].values > 0)
                        if "earn_next5" in latest.columns else False}, index=latest.index)
    return out, last
