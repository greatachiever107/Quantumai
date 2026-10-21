"""Do scheduled events (FOMC, NFP, anything in events/extra_events.csv) move
your stocks?

Run from the project folder (after fetch_stocks.py and build_events.py):
    python event_study.py

Method: for every event day, compare that day's absolute return with the
stock's normal move (average absolute return over the previous 20 days).
A multiple of 1.0 = a normal day; 1.5 = 50% bigger than normal. The result is
compared with ordinary (non-event) days using a Welch t-test, for the day
before (-1), the event day (0) and the day after (+1).
Pooled rows use ONE observation per event (the average across stocks) so that
stocks moving together are not counted as independent evidence.
Saves output/charts/event_study.png and output/processed/event_study_*.csv.
Educational only - not trading advice.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

OFFSETS = [-1, 0, 1]
EPS = 1e-9

df = pd.read_csv("data/stocks.csv", parse_dates=["Date"])
ret = (df.pivot(index="Date", columns="Ticker", values="daily_return_pct")
         .sort_index().dropna())
idx = ret.index
stocks = [t for t in ret.columns if t != "SPY"]

if not os.path.exists("events/events.csv"):
    raise SystemExit("events/events.csv not found - run build_events.py first.")
ev = pd.read_csv("events/events.csv", parse_dates=["date"])
ev["i"] = idx.searchsorted(ev["date"])            # event -> same/next trading day
ev = ev[(ev["i"] < len(idx)) & (ev["i"] >= 25)].copy()
ev = ev[(idx[ev["i"].clip(upper=len(idx) - 1)] - ev["date"]).dt.days.abs() <= 4]
types = sorted(ev["event"].unique())
print(f"{len(ev)} events inside your data: "
      + ", ".join(f"{t} ({(ev['event'] == t).sum()})" for t in types))

absr = ret.abs()
normal = absr.rolling(20).mean().shift(1)         # typical move before the day
logratio = np.log((absr + EPS) / (normal + EPS))
pooled = logratio[stocks].mean(axis=1)            # one number per day, across stocks

event_days = set()
for off in OFFSETS:
    event_days |= {j + off for j in ev["i"]}
non_event = np.array([j for j in range(25, len(idx)) if j not in event_days])


def test(vals, base):
    vals = np.asarray(vals, float)
    vals = vals[~np.isnan(vals)]
    if len(vals) < 5:
        return np.nan, np.nan
    mult = float(np.exp(vals.mean() - np.nanmean(base)))
    p = stats.ttest_ind(vals, base[~np.isnan(base)], equal_var=False).pvalue
    return mult, p


star = lambda p: "***" if p < .01 else "**" if p < .05 else "*" if p < .10 else ""

rows = []
for typ in types:
    ii = ev.loc[ev["event"] == typ, "i"].values
    for off in OFFSETS:
        m, p = test(pooled.iloc[ii + off].values, pooled.iloc[non_event].values)
        rows.append({"event": typ, "day": off, "n_events": len(ii),
                     "move_vs_normal_x": round(m, 2), "p_value": round(p, 4),
                     "sig": star(p)})
pool_df = pd.DataFrame(rows)
print("\n=== All stocks pooled: size of move vs a normal day ===")
print(pool_df.to_string(index=False))

rows = []
for typ in types:
    ii = ev.loc[ev["event"] == typ, "i"].values
    for t in stocks + ["SPY"]:
        m, p = test(logratio[t].iloc[ii].values, logratio[t].iloc[non_event].values)
        rows.append({"event": typ, "Ticker": t, "move_vs_normal_x": round(m, 2),
                     "p_value": round(p, 4), "sig": star(p)})
stock_df = pd.DataFrame(rows)
print("\n=== Event day by stock (x = multiple of a normal day's move) ===")
for typ in types:
    print(f"\n{typ}:")
    print(stock_df[stock_df.event == typ].drop(columns="event").to_string(index=False))

# direction: do event days tend to be up or down? (SPY, signed return)
rows = []
spy = ret["SPY"]
spy_z = spy / (normal["SPY"] + EPS)      # return in units of a "normal move": removes
rest = spy.iloc[non_event]               # the bigger-swings-on-event-days effect
rest_z = spy_z.iloc[non_event]
for typ in types:
    ii = ev.loc[ev["event"] == typ, "i"].values
    s = spy.iloc[ii]
    p = stats.ttest_ind(spy_z.iloc[ii], rest_z, equal_var=False).pvalue
    rows.append({"event": typ, "avg_SPY_return_pct": round(s.mean(), 3),
                 "normal_day_avg_pct": round(rest.mean(), 3),
                 "share_up_days_pct": round((s > 0).mean() * 100, 1),
                 "p_value": round(p, 3)})
dir_df = pd.DataFrame(rows)
print("\n=== Direction: average SPY return on event days vs normal days ===")
print(dir_df.to_string(index=False))

os.makedirs("output/charts", exist_ok=True)
os.makedirs("output/processed", exist_ok=True)
pool_df.to_csv("output/processed/event_study_pooled.csv", index=False)
stock_df.to_csv("output/processed/event_study_by_stock.csv", index=False)
dir_df.to_csv("output/processed/event_study_direction.csv", index=False)

cols = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [2, 3]})
w = 0.8 / len(types)
for k, typ in enumerate(types):
    sub = pool_df[pool_df.event == typ]
    a1.bar(np.arange(len(OFFSETS)) + k * w, sub["move_vs_normal_x"], w,
           label=typ, color=cols[k % len(cols)])
a1.axhline(1, color="black", lw=0.8)
a1.set_xticks(np.arange(len(OFFSETS)) + w * (len(types) - 1) / 2)
a1.set_xticklabels(["Day before", "Event day", "Day after"])
a1.set_ylabel("Move vs a normal day (1.0 = normal)")
a1.set_title("All stocks pooled")
a1.legend()
a1.grid(axis="y", alpha=0.3)

order = stock_df[stock_df.event == types[0]].sort_values("move_vs_normal_x")["Ticker"].tolist()
yy = np.arange(len(order))
for k, typ in enumerate(types):
    sub = stock_df[stock_df.event == typ].set_index("Ticker").loc[order]
    a2.barh(yy + k * w, sub["move_vs_normal_x"], w, label=typ, color=cols[k % len(cols)])
a2.axvline(1, color="black", lw=0.8)
a2.set_yticks(yy + w * (len(types) - 1) / 2)
a2.set_yticklabels(order)
a2.set_xlabel("Event-day move vs a normal day (1.0 = normal)")
a2.set_title("By stock")
a2.grid(axis="x", alpha=0.3)
fig.suptitle("Do scheduled events move the market?", fontsize=13)
fig.tight_layout()
fig.savefig("output/charts/event_study.png", dpi=150)
print("\nSaved output/charts/event_study.png and output/processed/event_study_*.csv")
print("Stars: * p<0.10, ** p<0.05, *** p<0.01. With many tests, a few stars happen by chance.")


# =====================================================================
# Earnings study (per stock; needs events/earnings.csv from fetch_earnings.py)
# =====================================================================
if os.path.exists("events/earnings.csv"):
    er = pd.read_csv("events/earnings.csv", parse_dates=["date"])
    er = er[er["Ticker"].isin(stocks) & er["timing"].isin(["BMO", "AMC"])].copy()
    p0 = idx.searchsorted(er["date"])
    er["i"] = p0 + (er["timing"] == "AMC").astype(int).values   # reaction day
    near = (idx[np.minimum(p0, len(idx) - 1)] - er["date"]).dt.days.abs() <= 4
    er = er[near & (er["i"] >= 25) & (er["i"] < len(idx) - 2)]
    print(f"\n\n{'=' * 60}\nEARNINGS: {len(er)} announcements with known timing "
          f"across {er['Ticker'].nunique()} stocks "
          f"({er['date'].min().date()} to {er['date'].max().date()})")

    rows, excess = [], {o: [] for o in OFFSETS}
    for t in stocks:
        ii = er.loc[er["Ticker"] == t, "i"].values
        if len(ii) < 5:
            continue
        near_e = set()
        for j in ii:
            near_e |= {j + o for o in OFFSETS}
        base = np.array([j for j in range(25, len(idx)) if j not in near_e])
        lr = logratio[t].values
        row = {"Ticker": t, "n": len(ii)}
        for o in OFFSETS:
            m, p = test(lr[ii + o], lr[base])
            row[f"day{o:+d}_x"] = round(m, 2)
            row[f"day{o:+d}_sig"] = star(p)
            excess[o] += list(lr[ii + o] - np.nanmean(lr[base]))
        a = absr[t].values
        row["earn_day_median_abs_%"] = round(float(np.median(a[ii])), 2)
        row["normal_day_median_abs_%"] = round(float(np.median(a[base])), 2)
        rows.append(row)
    earn_stock = pd.DataFrame(rows)
    print("\n=== Earnings day vs a normal day, by stock (x = multiple of normal move) ===")
    print(earn_stock.to_string(index=False))

    rows = []
    for o in OFFSETS:
        e = np.array(excess[o], float)
        e = e[~np.isnan(e)]
        rows.append({"day": o, "n_events": len(e),
                     "move_vs_normal_x": round(float(np.exp(e.mean())), 2),
                     "p_value": round(float(stats.ttest_1samp(e, 0).pvalue), 4)})
    earn_pool = pd.DataFrame(rows)
    earn_pool["sig"] = earn_pool["p_value"].map(star)
    print("\n=== All earnings pooled ===")
    print(earn_pool.to_string(index=False))

    # Does the SURPRISE matter? (reported EPS vs analyst estimate)
    sv = er.dropna(subset=["eps_surprise_pct"]).copy()
    if len(sv) >= 30:
        sv["ret"] = [ret[t].iloc[i] for t, i in zip(sv["Ticker"], sv["i"])]
        sv["z"] = [ret[t].iloc[i] / (normal[t].iloc[i] + EPS) for t, i in zip(sv["Ticker"], sv["i"])]
        rho, pr_ = stats.spearmanr(sv["eps_surprise_pct"], sv["z"])
        beat, miss = sv[sv["eps_surprise_pct"] > 0], sv[sv["eps_surprise_pct"] < 0]
        print("\n=== Does the earnings surprise move the price? ===")
        print(f"Announcements with a known surprise: {len(sv)}")
        print(f"Rank correlation, surprise % vs reaction-day return: {rho:+.2f} (p = {pr_:.4f})")
        print(f"Beat estimate:  {len(beat):4d} cases, average reaction-day return {beat['ret'].mean():+.2f}%")
        print(f"Missed estimate: {len(miss):3d} cases, average reaction-day return {miss['ret'].mean():+.2f}%")
        print("(A beat does not guarantee a rise: the price already expects a beat.)")
    else:
        sv = None
        print("\nNot enough earnings-surprise data to test direction.")

    earn_stock.to_csv("output/processed/earnings_study_by_stock.csv", index=False)
    earn_pool.to_csv("output/processed/earnings_study_pooled.csv", index=False)

    fig, (b1, b2) = plt.subplots(1, 2, figsize=(13, 6))
    es = earn_stock.sort_values("day+0_x")
    yy = np.arange(len(es))
    b1.barh(yy, es["day+0_x"], color="#2563eb")
    b1.axvline(1, color="black", lw=0.8)
    b1.set_yticks(yy)
    b1.set_yticklabels(es["Ticker"])
    b1.set_xlabel("Earnings-day move vs a normal day (1.0 = normal)")
    b1.set_title("How much bigger are earnings days?")
    b1.grid(axis="x", alpha=0.3)
    if sv is not None:
        b2.scatter(sv["eps_surprise_pct"].clip(-50, 50), sv["ret"], s=14, alpha=0.5,
                   color="#2563eb")
        b2.axhline(0, color="black", lw=0.8)
        b2.axvline(0, color="black", lw=0.8)
        b2.set_xlabel("EPS surprise (%, clipped to +/-50)")
        b2.set_ylabel("Reaction-day return (%)")
        b2.set_title(f"Surprise vs price reaction (rank corr {rho:+.2f})")
        b2.grid(alpha=0.3)
    else:
        b2.axis("off")
    fig.suptitle("Earnings study", fontsize=13)
    fig.tight_layout()
    fig.savefig("output/charts/earnings_study.png", dpi=150)
    print("\nSaved output/charts/earnings_study.png and output/processed/earnings_study_*.csv")
else:
    print("\n(No events/earnings.csv - run fetch_earnings.py to add the earnings study.)")
