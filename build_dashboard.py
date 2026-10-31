"""Build dashboard/index.html from the results in output/processed/.

    python build_dashboard.py
Open dashboard/index.html by double-clicking it, or deploy the dashboard folder
(e.g. `vercel dashboard`). Re-run after each refresh to update the numbers.
"""
import json, os
import pandas as pd

P = "output/processed/"
def rd(name, **kw):
    f = P + name
    return pd.read_csv(f, **kw).where(lambda d: d.notna(), None) if os.path.exists(f) else None
def rec(df):
    return [] if df is None else json.loads(df.to_json(orient="records"))

fc = rd("volatility_forecast.csv")
cal = rd("interval_calibration.csv")
sm = rd("model_volatility_v3_summary.csv")
if sm is not None:
    sm = sm.rename(columns={sm.columns[0]: "method"})
asof = ""
if os.path.exists("data/stocks.csv"):
    asof = str(pd.read_csv("data/stocks.csv", usecols=["Date"])["Date"].max())[:10]
data = {"asof": asof, "forecast": rec(fc), "models": rec(sm),
        "events": rec(rd("event_study_pooled.csv")),
        "tracking": rec((pd.read_csv("output/tracking/tracking_summary.csv") if os.path.exists("output/tracking/tracking_summary.csv") else None)),
        "earnings": rec(rd("earnings_study_by_stock.csv")),
        "earn_pool": rec(rd("earnings_study_pooled.csv")),
        "calib": rec(cal)}

HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>US Stocks Volatility Dashboard</title><style>
:root{--bg:#fff;--fg:#111827;--mut:#6b7280;--card:#f3f4f6;--a:#2563eb;--g:#9ca3af;--up:#16a34a;--dn:#dc2626}
@media(prefers-color-scheme:dark){:root{--bg:#0f172a;--fg:#e5e7eb;--mut:#94a3b8;--card:#1e293b;--a:#60a5fa;--g:#64748b;--up:#4ade80;--dn:#f87171}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px system-ui,sans-serif;padding:20px;max-width:960px;margin:auto}
h1{margin:0 0 4px;font-size:22px}h2{font-size:16px;margin:0 0 10px}.mut{color:var(--mut);font-size:13px}
.card{background:var(--card);border-radius:12px;padding:16px;margin:16px 0}
.row{display:grid;grid-template-columns:90px 1fr 96px;align-items:center;gap:8px;margin:5px 0}
.bar{height:9px;border-radius:5px;margin:2px 0}table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:5px 6px;text-align:right}td:first-child,th:first-child{text-align:left}th{color:var(--mut);font-weight:500}
.star{color:#f59e0b}.x{position:relative;height:16px;background:var(--bg);border-radius:4px}
.x i{position:absolute;left:0;top:0;height:100%;border-radius:4px;background:var(--a)}
.x b{position:absolute;top:-2px;bottom:-2px;width:2px;background:var(--fg)}
.rg{position:relative;height:7px;margin:2px 0}.rg i{position:absolute;top:0;height:7px;box-sizing:border-box;border-left:1px solid var(--fg);border-right:1px solid var(--fg);background:linear-gradient(var(--fg),var(--fg)) center/100% 1px no-repeat;opacity:.75}</style></head><body>
<h1>US Stocks Volatility Dashboard</h1><div class="mut" id="sub"></div>
<div class="card"><h2>Next-5-day volatility forecast (annualized %)</h2>
<div class="mut">Grey = last 20 days, blue = forecast. The thin line is the 80% range: where real volatility landed 80% of the time in backtests. &#9733; = earnings due in the window. Describes the size of swings, not price direction.</div>
<div id="fc"></div></div>
<div class="card"><h2>How reliable are the ranges?</h2><table id="cal"></table>
<div class="mut">Share of past weeks where real volatility landed inside the 80% range (tested on weeks the range had never seen). Target is 80%. Below that, the range is too narrow.</div></div>
<div class="card"><h2>Model scorecard (walk-forward backtest)</h2><table id="md"></table>
<div class="mut">MAE/QLIKE: lower is better. Naive = &ldquo;next week looks like the last 20 days&rdquo;.</div></div>
<div class="card"><h2>Forecast tracking (scored on what actually happened)</h2><table id="tk"></table>
<div class="mut">&ldquo;live&rdquo; = forecasts saved in real time; &ldquo;backfill&rdquo; = rebuilt using only past data. Big call = forecast differs from recent by 10%+. &ldquo;Vol direction hit&rdquo; = how often the forecast correctly called volatility rising or falling. It says nothing about whether prices rise or fall.</div></div>
<div class="card"><h2>How much bigger are earnings days? (multiple of a normal day)</h2><div id="er"></div></div>
<div class="card"><h2>Scheduled macro events, all stocks pooled</h2><table id="ev"></table></div>
<div class="mut">Educational only &mdash; not trading advice.</div>
<script>const D=__DATA__;const $=i=>document.getElementById(i);
$('sub').textContent='Data through '+(D.asof||'n/a');
const mx=Math.max(1,...D.forecast.map(r=>Math.max(r.recent_20d_vol_ann_pct,r.forecast_5d_vol_ann_pct,r.forecast_high_ann_pct||0)));
$('fc').innerHTML=[...D.forecast].reverse().map(r=>{const c=r.forecast_vs_recent_pct,col='var(--a)';
return `<div class="row"><div>${r.Ticker}${r.earnings_in_window?' <span class="star">&#9733;</span>':''}</div><div>
<div class="bar" style="width:${r.recent_20d_vol_ann_pct/mx*100}%;background:var(--g)"></div>
<div class="bar" style="width:${r.forecast_5d_vol_ann_pct/mx*100}%;background:var(--a)"></div>
${r.forecast_low_ann_pct==null?'':`<div class="rg"><i style="left:${r.forecast_low_ann_pct/mx*100}%;width:${(r.forecast_high_ann_pct-r.forecast_low_ann_pct)/mx*100}%"></i></div>`}</div>
<div style="text-align:right">${Number(r.forecast_5d_vol_ann_pct).toFixed(1)}%${r.forecast_low_ann_pct==null?'':`<br><span class="mut" style="font-size:11px">${Number(r.forecast_low_ann_pct).toFixed(1)}\u2013${Number(r.forecast_high_ann_pct).toFixed(1)}</span>`}<br><span style="color:${col};font-size:12px">${c>=0?'\u25B2':'\u25BC'} ${Math.abs(c)}%</span></div></div>`}).join('')||'<div class="mut">Run volatility_chart.py first.</div>';
const nm={normal:'No earnings in window',earnings:'Earnings in window'};
$('cal').innerHTML=D.calib.length?'<tr><th>Situation</th><th>Forecasts scored</th><th>Landed inside range</th></tr>'+D.calib.map(c=>`<tr><td>${nm[c.window]||c.window}</td><td>${c.n}</td><td style="color:${c.oos_coverage_pct<76?'var(--dn)':'var(--up)'}">${c.oos_coverage_pct}%${c.oos_coverage_pct<76?' (too narrow)':''}</td></tr>`).join(''):'<tr><td class="mut">Run model_volatility_v3.py once to measure this.</td></tr>';
$('tk').innerHTML=D.tracking.length?'<tr><th>Set</th><th>Scored</th><th>Model err</th><th>Naive err</th><th>Closer than naive</th><th>Vol direction hit</th><th>Big-call hit</th></tr>'+D.tracking.map(t=>`<tr><td>${t.source}</td><td>${t.forecasts}</td><td>${t.ens_mae}</td><td>${t.naive_mae}</td><td>${t.closer_than_naive_pct}%</td><td>${t.direction_hit_pct}%</td><td>${t.big_call_hit_pct==null?'-':t.big_call_hit_pct+'% ('+t.big_calls+')'}</td></tr>`).join(''):'<tr><td class="mut">Run track_forecasts.py first (add --backfill 26 for instant results).</td></tr>';
$('md').innerHTML=D.models.length?'<tr><th>Method</th><th>MAE</th><th>QLIKE</th><th>vs naive</th></tr>'+D.models.map(m=>`<tr><td>${m.method}</td><td>${m.avg_MAE}</td><td>${m.avg_QLIKE}</td><td>${m['MAE_vs_naive_%']}%</td></tr>`).join(''):'<tr><td class="mut">Run model_volatility_v3.py first.</td></tr>';
const em=Math.max(1,...D.earnings.map(r=>r['day+0_x']));
$('er').innerHTML=[...D.earnings].sort((a,b)=>b['day+0_x']-a['day+0_x']).map(r=>`<div class="row"><div>${r.Ticker}</div><div class="x"><i style="width:${r['day+0_x']/em*100}%"></i><b style="left:${1/em*100}%"></b></div><div style="text-align:right">${r['day+0_x']}&times;</div></div>`).join('')+(D.earn_pool.length?`<div class="mut">Pooled earnings day: ${(D.earn_pool.find(r=>r.day==0)||{}).move_vs_normal_x}&times; normal. Black tick = normal day.</div>`:'')||'<div class="mut">Run fetch_earnings.py and event_study.py first.</div>';
$('ev').innerHTML=D.events.length?'<tr><th>Event</th><th>Day</th><th>Move vs normal</th><th>p-value</th></tr>'+D.events.map(r=>`<tr><td>${r.event}</td><td>${r.day>0?'+':''}${r.day}</td><td>${r.move_vs_normal_x}&times;</td><td>${r.p_value}</td></tr>`).join(''):'<tr><td class="mut">Run event_study.py first.</td></tr>';
</script></body></html>"""

os.makedirs("dashboard", exist_ok=True)
with open("dashboard/index.html", "w", encoding="utf-8") as f:
    f.write(HTML.replace("__DATA__", json.dumps(data)))
print("Saved dashboard/index.html  (open it in your browser)")
