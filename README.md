# Python Data Lab - US Stock Volatility Forecasting

A local Python project that downloads US stock data, tests forecasting models
honestly against simple baselines, and publishes a dashboard of next-week
volatility forecasts with live accuracy tracking.

**What it forecasts:** how large price swings (volatility) will be over the next
5 trading days for 10 US stocks. **What it does not do:** predict price direction.
In testing, up/down prediction was no better than a coin flip, so it is not
offered. Educational project - not trading advice.

## Setup (Windows PowerShell)

Run everything from the folder that contains `main.py`.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest        # optional: tests for the original data lab
```

## Weekly use (one command)

```powershell
.\.venv\Scripts\python.exe run_weekly.py            # refresh + forecast + dashboard
.\.venv\Scripts\python.exe run_weekly.py --full     # also rerun the full model backtest
Invoke-Item .\dashboard\index.html
```

It clears the download caches (they never expire on their own), then runs the
steps below in order and stops at the first failure. If Yahoo blocks a download
("possibly delisted" is usually a temporary block), wait a few minutes and rerun.

## What each script does

| Script | Purpose |
|---|---|
| `fetch_stocks.py` | 10 years of prices for 10 stocks + SPY, one ticker at a time with retries -> `data/stocks.csv` |
| `build_events.py` | FOMC and jobs-report (NFP) calendar -> `events/events.csv`. Add your own (CPI, elections...) in `events/extra_events.csv` as `date,event` |
| `fetch_earnings.py` | Earnings dates, timing and EPS surprises -> `events/earnings.csv` |
| `event_study.py` | Do FOMC / NFP / earnings days move the stocks more than normal? Charts + CSVs |
| `volfeatures.py` | Shared feature engineering (range volatility, gaps, market stress, events, earnings) |
| `model_volatility_v3.py` | Walk-forward backtest of all models. Flags: `--no-events`, `--no-earnings` |
| `volatility_chart.py` | Trains the ensemble on all history and forecasts the next 5 days |
| `track_forecasts.py` | Logs each forecast, scores it after 5 days. `--backfill 26` rebuilds past weeks using only data available then |
| `build_dashboard.py` | Builds `dashboard/index.html` (single self-contained page) |
| `position_sizing.py` | Backtest: risk-based position sizing vs equal weights |
| `model_stocks.py`, `model_volatility.py` | Earlier model versions (market beta, direction test, v2 volatility) |
| `main.py` | The original data-analysis lab for any CSV (`main.py run`) |

Note: `main.py run` analyses every CSV in `data/`, including `stocks.csv`.

## Model in one paragraph

An ensemble: the average of (1) an EWMA volatility estimate, (2) a pooled ridge
regression and (3) a pooled gradient-boosting model, trained on all stocks at
once to predict log volatility over the next 5 days. Inputs: close-to-close and
High-Low range volatility, overnight gaps, 1-year volatility level, SPY market
stress, FOMC/NFP in the window, and per-stock earnings (next 5 / last 5 / last 20
days). All testing is walk-forward with a 5-day gap so training never overlaps
the test period.

## Key results (so far)

- Ensemble forecast error about 15% below the naive "same as last 20 days" rule
  across 5 time periods and all 10 stocks (long backtest); about 19% lower in a
  26-week backfill. Earnings features helped most in earnings weeks.
- Earnings days move stocks about 3x a normal day; FOMC about 1.2x; jobs reports
  show up at the market level (SPY) but not clearly in single stocks.
- Beating or missing EPS estimates relates only modestly to the price reaction
  (rank correlation about +0.27); misses are punished much harder than beats.

## Honest limitations

- **Only "live" tracking is a real test.** The backfill is rebuilt from past data
  after the model was designed, so it can be unconsciously tuned. Check the
  `live` row on the dashboard as weeks accumulate.
- 10 large US stocks that are today's winners (survivorship bias); the 10 stocks
  move together, so independent evidence is far less than the row counts suggest.
- Data comes from Yahoo Finance via `yfinance`: unofficial, can be rate-limited,
  and **not licensed for a commercial product**. Use a licensed provider
  (e.g. Polygon, Alpaca) before monetising.
- Future earnings dates beyond a few weeks are estimates and may shift.
- Volatility forecasts describe the size of swings, never their direction.

## Output files

- `output/charts/` - PNG charts; `output/processed/` - result CSVs
- `output/tracking/` - `forecast_log.csv`, `forecast_scored.csv`, `tracking_summary.csv`
- `dashboard/index.html` - deploy with `vercel dashboard`, or open locally

## Troubleshooting

- *"requirements.txt not found" / files missing:* you are in the outer folder;
  `cd` into the inner `Python-Data-Lab` folder that holds `main.py`.
- *Some tickers fail to download:* wait 5-10 minutes, rerun `fetch_stocks.py`
  (successful tickers are cached in `cache_prices/`).
- *"Forecast file is older than the price data":* run `volatility_chart.py`
  before `track_forecasts.py` (`run_weekly.py` already does).
