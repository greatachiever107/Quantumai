"""StockAI API v0.1 - serves the existing pipeline's results.

Run from the PROJECT folder (the one with main.py and output/):
    python -m uvicorn backend.main:app --reload
Docs: http://127.0.0.1:8000/docs
Every response says whether it is real project data ("live-data") or labelled
DEMO sample data ("demo"). Demo data is never mixed with real data.
No authentication yet - local use only.
"""
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(os.getenv("PROJECT_DIR", Path(__file__).resolve().parent.parent))
P, T = ROOT / "output/processed", ROOT / "output/tracking"
WL_FILE = ROOT / "backend/watchlist.json"
DEFAULT_WL = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "JPM", "V", "WMT", "XOM", "JNJ"]
RANGES = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252, "5Y": 1260, "ALL": None}

app = FastAPI(title="StockAI API", version="0.1.0")
ACCESS_KEY = os.getenv("ACCESS_KEY", "")      # set on the server to make the API private


async def gate(request: Request, call_next):
    """If ACCESS_KEY is set, every /api/v1 call except /health needs a matching X-Access-Key header."""
    path = request.url.path
    if ACCESS_KEY and request.method != "OPTIONS" and path.startswith("/api/v1") and path != "/api/v1/health":
        if not secrets.compare_digest(request.headers.get("x-access-key", ""), ACCESS_KEY):
            return JSONResponse({"detail": "locked"}, status_code=401)
    return await call_next(request)


app.middleware("http")(gate)               # added BEFORE CORS so CORS headers also reach 401 replies
app.add_middleware(CORSMiddleware,
                   allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
                   allow_methods=["GET", "PUT"], allow_headers=["*"])


def read(path):
    return pd.read_csv(path) if Path(path).exists() else None


class Forecast(BaseModel):
    ticker: str
    recent_vol_ann_pct: float
    forecast_vol_ann_pct: float
    change_pct: float
    typical_daily_move_pct: float
    earnings_in_window: bool
    next_earnings: str | None = None
    regime: str | None = None          # Calm / Normal / Elevated / High (vs the stock's own history)


class ForecastsResponse(BaseModel):
    data_mode: str
    as_of: str | None
    horizon_trading_days: int = 5
    note: str
    items: list[Forecast]


class Candle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class CandlesResponse(BaseModel):
    data_mode: str
    ticker: str
    candles: list[Candle]


def prices():
    f = ROOT / "data/stocks.csv"
    return pd.read_csv(f, parse_dates=["Date"]) if f.exists() else None


def regime(ticker, daily_vol, px):
    """Where today's forecast sits in the stock's own history of 20-day volatility."""
    if px is None:
        return None
    r = px[px["Ticker"] == ticker].sort_values("Date")["daily_return_pct"].rolling(20).std().dropna()
    if len(r) < 100:
        return None
    pct = float((r < daily_vol).mean() * 100)
    return "Calm" if pct < 25 else "Normal" if pct < 75 else "Elevated" if pct < 90 else "High"


def demo_series(ticker, n=300):
    rng = np.random.default_rng(sum(ord(c) for c in ticker))
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, n)))
    op = np.r_[close[0], close[:-1]]
    hi, lo = np.maximum(op, close) * 1.005, np.minimum(op, close) * 0.995
    return pd.DataFrame({"Date": pd.bdate_range(end="2026-01-02", periods=n).strftime("%Y-%m-%d"),
                         "Open": op, "High": hi, "Low": lo, "Close": close,
                         "Volume": rng.integers(1_000_000, 5_000_000, n).astype(float)})


@app.get("/api/v1/health")
def health():
    files = {"forecast": (P / "volatility_forecast.csv").exists(),
             "prices": (ROOT / "data/stocks.csv").exists(),
             "tracking": (T / "tracking_summary.csv").exists(),
             "model_summary": (P / "model_volatility_v3_summary.csv").exists()}
    return {"status": "ok", "project_dir": str(ROOT), "files_found": files,
            "mode": "live-data" if files["forecast"] else "demo", "news_configured": bool(NEWS_KEY or FINNHUB_KEY)}


@app.get("/api/v1/forecasts", response_model=ForecastsResponse)
def forecasts():
    f = read(P / "volatility_forecast.csv")
    if f is None:
        rng = np.random.default_rng(1)
        items = []
        for t in ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA"]:
            rec = float(rng.uniform(15, 35))
            fc = rec * float(rng.uniform(0.85, 1.3))
            items.append(Forecast(ticker=t, recent_vol_ann_pct=round(rec, 1),
                                  forecast_vol_ann_pct=round(fc, 1),
                                  change_pct=round((fc / rec - 1) * 100, 1),
                                  typical_daily_move_pct=round(fc / 15.87, 2),
                                  earnings_in_window=False, regime="Normal"))
        return ForecastsResponse(data_mode="demo", as_of=None, items=items,
                                 note="DEMO DATA: random sample values, not real forecasts. "
                                      "Run volatility_chart.py to see real ones.")
    px = prices()
    items = [Forecast(
        ticker=r["Ticker"], recent_vol_ann_pct=r["recent_20d_vol_ann_pct"],
        forecast_vol_ann_pct=r["forecast_5d_vol_ann_pct"], change_pct=r["forecast_vs_recent_pct"],
        typical_daily_move_pct=r["typical_daily_move_pct"],
        earnings_in_window=bool(r.get("earnings_in_window", False)),
        next_earnings=None if pd.isna(r.get("next_earnings")) else str(r["next_earnings"]),
        regime=regime(r["Ticker"], r["typical_daily_move_pct"], px))
        for _, r in f.iterrows()]
    as_of = str(px["Date"].max().date()) if px is not None else None
    return ForecastsResponse(
        data_mode="live-data", as_of=as_of, items=items,
        note="Forecasts the SIZE of price swings, not direction. Educational; not financial advice.")


@app.get("/api/v1/forecasts/{ticker}", response_model=Forecast)
def forecast_one(ticker: str):
    for it in forecasts().items:
        if it.ticker == ticker.upper():
            return it
    raise HTTPException(404, f"No forecast for {ticker.upper()}")


@app.get("/api/v1/candles/{ticker}", response_model=CandlesResponse)
def candles(ticker: str, range: str = Query("1Y", pattern="^(1M|3M|6M|1Y|5Y|ALL)$")):
    t, px = ticker.upper(), prices()
    if px is None:
        d, mode = demo_series(t), "demo"
    else:
        d = px[px["Ticker"] == t].sort_values("Date")
        if d.empty:
            raise HTTPException(404, f"No price data for {t}")
        d = d.assign(Date=d["Date"].dt.strftime("%Y-%m-%d"))
        mode = "live-data"
    if RANGES[range]:
        d = d.tail(RANGES[range])
    return CandlesResponse(data_mode=mode, ticker=t, candles=[
        Candle(date=r.Date, open=r.Open, high=r.High, low=r.Low, close=r.Close,
               volume=None if "Volume" not in d or pd.isna(r.Volume) else r.Volume)
        for r in d.itertuples()])


@app.get("/api/v1/tracking/summary")
def tracking_summary():
    s = read(T / "tracking_summary.csv")
    return {"data_mode": "live-data" if s is not None else "none",
            "note": "'live' = forecasts saved in real time; 'backfill' = rebuilt from past data (not a live record).",
            "items": [] if s is None else json.loads(s.to_json(orient="records"))}


@app.get("/api/v1/tracking/scored")
def tracking_scored(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    s = read(T / "forecast_scored.csv")
    if s is None:
        return {"data_mode": "none", "total": 0, "items": []}
    s = s.sort_values("as_of", ascending=False)
    return {"data_mode": "live-data", "total": len(s),
            "items": json.loads(s.iloc[offset:offset + limit].to_json(orient="records"))}


@app.get("/api/v1/models/summary")
def models_summary():
    s = read(P / "model_volatility_v3_summary.csv")
    if s is None:
        return {"data_mode": "none", "items": []}
    s = s.rename(columns={s.columns[0]: "method"})
    return {"data_mode": "live-data", "note": "Walk-forward backtest; lower MAE/QLIKE is better.",
            "items": json.loads(s.to_json(orient="records"))}


@app.get("/api/v1/calendar")
def calendar(days: int = Query(30, ge=1, le=120)):
    today = pd.Timestamp.today().normalize()
    end = today + pd.Timedelta(days=days)
    out = []
    ev, er = read(ROOT / "events/events.csv"), read(ROOT / "events/earnings.csv")
    if ev is not None:
        ev["date"] = pd.to_datetime(ev["date"])
        out += [{"date": str(r.date.date()), "type": r.event, "ticker": None}
                for r in ev[(ev["date"] >= today) & (ev["date"] <= end)].itertuples()]
    if er is not None:
        er["date"] = pd.to_datetime(er["date"])
        out += [{"date": str(r.date.date()), "type": "EARNINGS", "ticker": r.Ticker}
                for r in er[(er["date"] >= today) & (er["date"] <= end)].itertuples()]
    return {"data_mode": "live-data" if out else "none",
            "items": sorted(out, key=lambda x: x["date"])}


@app.get("/api/v1/models/by-stock")
def models_by_stock():
    s = read(P / "model_volatility_v3_by_stock.csv")
    return {"data_mode": "none" if s is None else "live-data",
            "items": [] if s is None else json.loads(s.to_json(orient="records"))}


@app.get("/api/v1/backtest/sizing")
def backtest_sizing():
    """Risk-based position sizing backtest (run position_sizing.py to create it)."""
    res, eq = read(P / "position_sizing_results.csv"), read(P / "position_sizing_equity.csv")
    if res is None:
        return {"data_mode": "none", "results": [], "equity": {}}
    curves = {}
    if eq is not None:
        step = max(1, len(eq) // 600)                       # keep the payload small
        for c in eq.columns[1:]:
            curves[c] = [{"time": d, "value": float(v)} for d, v in zip(eq.iloc[::step, 0], eq[c].iloc[::step])]
    return {"data_mode": "live-data",
            "note": "Weekly rebalance, 5 bp cost per unit of turnover, walk-forward forecasts. "
                    "Stocks are today's large winners (survivorship bias), so absolute returns are flattered.",
            "results": json.loads(res.to_json(orient="records")), "equity": curves}


@app.get("/api/v1/quotes")
def quotes():
    px = prices()
    if px is None:
        return {"data_mode": "none", "items": []}
    last = px.sort_values("Date").groupby("Ticker").tail(1)
    return {"data_mode": "live-data", "note": "End-of-day closing prices (not real-time).",
            "items": [{"ticker": r.Ticker, "close": float(r.Close), "date": str(r.Date.date())}
                      for r in last.itertuples()]}


@app.get("/api/v1/overview")
def overview():
    """Market stress (SPY) plus forecast risk by sector, from the project's own results."""
    f, px = forecasts(), prices()
    if f.data_mode != "live-data" or px is None:
        return {"data_mode": "none"}
    sec = {}
    if "Sector" in px.columns:
        sec = px.drop_duplicates("Ticker").set_index("Ticker")["Sector"].to_dict()
    spy_vol = spy_reg = None
    spy = px[px["Ticker"] == "SPY"].sort_values("Date")["daily_return_pct"].rolling(20).std().dropna()
    if len(spy):
        spy_vol = round(float(spy.iloc[-1]) * 252 ** 0.5, 1)
        spy_reg = regime("SPY", float(spy.iloc[-1]), px)
    groups = {}
    for it in f.items:
        groups.setdefault(sec.get(it.ticker, "Other"), []).append(it)
    counts = {}
    for it in f.items:
        counts[it.regime or "Unknown"] = counts.get(it.regime or "Unknown", 0) + 1
    return {"data_mode": "live-data", "as_of": f.as_of, "spy_recent_vol_ann_pct": spy_vol, "spy_regime": spy_reg,
            "regime_counts": counts, "rising": sum(i.change_pct > 0 for i in f.items),
            "falling": sum(i.change_pct <= 0 for i in f.items),
            "earnings_in_window": [i.ticker for i in f.items if i.earnings_in_window],
            "sectors": [{"sector": k, "stocks": len(v),
                         "avg_forecast_vol_ann_pct": round(sum(i.forecast_vol_ann_pct for i in v) / len(v), 1),
                         "avg_change_pct": round(sum(i.change_pct for i in v) / len(v), 1)}
                        for k, v in groups.items()]}


@app.get("/api/v1/trend")
def trend():
    """Descriptive trend context from past prices. NOT a forecast of direction."""
    px = prices()
    if px is None:
        return {"data_mode": "none", "items": []}
    items = []
    for t, g in px.sort_values("Date").groupby("Ticker"):
        c = g["Close"].reset_index(drop=True)
        if len(c) < 210:
            continue
        last, s50, s200 = float(c.iloc[-1]), float(c.tail(50).mean()), float(c.tail(200).mean())
        hi = float(c.tail(252).max())

        def ret(n):
            return round((last / float(c.iloc[-1 - n]) - 1) * 100, 1) if len(c) > n else None

        label = "Uptrend" if last > s50 > s200 else "Downtrend" if last < s50 < s200 else "Mixed"
        items.append({"ticker": t, "close": round(last, 2), "label": label,
                      "vs_sma50_pct": round((last / s50 - 1) * 100, 1),
                      "vs_sma200_pct": round((last / s200 - 1) * 100, 1),
                      "ret_1m_pct": ret(21), "ret_3m_pct": ret(63), "ret_12m_pct": ret(252),
                      "off_52w_high_pct": round((last / hi - 1) * 100, 1)})
    return {"data_mode": "live-data" if items else "none",
            "note": "Describes where the price has been. It is not a forecast of where it is going.",
            "items": items}


# ---------------------------------------------------------------- news & sentiment
NEWS_KEY = os.getenv("NEWS_API_KEY", "")            # Alpha Vantage (its news endpoint is premium-only now)
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")      # Finnhub: free plan includes company news
_news_cache = {"at": 0.0, "key": "", "items": []}

POS = set("""beat beats surge surges soar soars jump jumps rally rallies gain gains rise rises record upgrade upgrades
raise raises raised strong growth profit profits outperform bullish boost boosts win wins approval approved expands
expansion breakthrough higher tops topped climb climbs optimism""".split())
NEG = set("""miss misses missed fall falls drop drops plunge plunges slump slumps tumble tumbles decline declines cut cuts
downgrade downgrades lawsuit sue sues probe investigation recall fraud warning warns weak loss losses bearish slide
slides sink sinks lower layoffs layoff fined ban bans delay delays fears risk crash""".split())


def headline_tone(title):
    """Very simple keyword tone of a headline: approximate, English only."""
    words = re.findall(r"[a-z]+", title.lower())
    p, n = sum(w in POS for w in words), sum(w in NEG for w in words)
    score = round((p - n) / (p + n), 2) if p + n else 0.0
    return ("Positive" if p > n else "Negative" if n > p else "Neutral"), score


def finnhub_fetch(key, symbols):
    """Finnhub GET /company-news for each symbol (one symbol per call), last 7 days."""
    import httpx
    to = datetime.now(timezone.utc).date()
    out = {}
    with httpx.Client(timeout=20, headers={"X-Finnhub-Token": key}) as c:
        for sym in symbols:
            r = c.get("https://finnhub.io/api/v1/company-news",
                      params={"symbol": sym, "from": str(to - timedelta(days=7)), "to": str(to)})
            if r.status_code == 429:
                raise RuntimeError("rate limit reached")
            r.raise_for_status()
            data = r.json()
            out[sym] = data[:15] if isinstance(data, list) else []
    return out


def normalise_finnhub(data):
    merged = {}
    for sym, arts in data.items():
        for a in arts:
            url, title = a.get("url"), a.get("headline")
            if not url or not title:
                continue
            m = merged.get(url)
            if m is None:
                tone_, sc = headline_tone(title)
                try:
                    when = datetime.fromtimestamp(int(a["datetime"]), timezone.utc).isoformat()
                except (KeyError, TypeError, ValueError, OSError):
                    when = None
                m = merged[url] = {"title": title, "url": url, "publisher": a.get("source"), "published_at": when,
                                   "tickers": [], "sentiment": tone_, "score": sc}
            if all(t["ticker"] != sym for t in m["tickers"]):
                m["tickers"].append({"ticker": sym, "sentiment": m["sentiment"], "score": m["score"]})
    return list(merged.values())


def av_fetch(key):
    """One Alpha Vantage NEWS_SENTIMENT call (premium plans only)."""
    import httpx
    r = httpx.get("https://www.alphavantage.co/query",
                  params={"function": "NEWS_SENTIMENT", "apikey": key}, timeout=30)
    r.raise_for_status()
    return r.json()


def tone(label):
    s = (label or "").lower()
    return "Positive" if "bull" in s else "Negative" if "bear" in s else "Neutral"


def normalise_news(raw, watch):
    """Alpha Vantage: keep articles clearly about a watched stock (relevance >= 0.3). Headline + link only."""
    items = []
    for a in raw.get("feed", []) or []:
        hits = []
        for ts in a.get("ticker_sentiment", []) or []:
            try:
                rel = float(ts.get("relevance_score", 0))
                sc = float(ts.get("ticker_sentiment_score", 0))
            except (TypeError, ValueError):
                continue
            if ts.get("ticker") in watch and rel >= 0.3:
                hits.append({"ticker": ts["ticker"], "sentiment": tone(ts.get("ticker_sentiment_label")), "score": round(sc, 3)})
        if not hits or not a.get("title") or not a.get("url"):
            continue
        try:
            when = datetime.strptime(a["time_published"], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc).isoformat()
        except (KeyError, ValueError):
            when = None
        try:
            overall = round(float(a.get("overall_sentiment_score")), 3)
        except (TypeError, ValueError):
            overall = None
        items.append({"title": a["title"], "url": a["url"], "publisher": a.get("source"), "published_at": when,
                      "tickers": hits, "sentiment": tone(a.get("overall_sentiment_label")), "score": overall})
    return items


@app.get("/api/v1/news")
def news(ticker: str | None = None, sentiment: str | None = Query(None, pattern="^(Positive|Negative|Neutral)$"),
         limit: int = Query(40, ge=1, le=100)):
    prov = "finnhub" if FINNHUB_KEY else "alphavantage" if NEWS_KEY else None
    base = {"source": "Finnhub company news" if prov == "finnhub" else "Alpha Vantage News & Sentiment",
            "note": ("Tone is a simple keyword estimate from each headline's wording (approximate, English only). "
                     "It describes the wording of the headline, not where the price will go.") if prov == "finnhub" else
                    "Sentiment describes the tone of each article as scored by Alpha Vantage. It is not a price prediction."}
    if not prov:
        return {**base, "data_mode": "none", "items": [], "stale": False,
                "note": "No news key configured. Set FINNHUB_API_KEY (free at finnhub.io) to enable headlines."}
    watch = sorted(set(get_watchlist().tickers) | {i.ticker for i in forecasts().items})
    key = prov + ":" + ",".join(watch)
    ttl = 1800 if prov == "finnhub" else 3 * 3600
    stale = False
    if _news_cache["key"] != key or time.time() - _news_cache["at"] > ttl:
        try:
            if prov == "finnhub":
                fresh = normalise_finnhub(finnhub_fetch(FINNHUB_KEY, [t for t in watch if t != "SPY"][:15]))
            else:
                raw = av_fetch(NEWS_KEY)
                msg = raw.get("Information") or raw.get("Note") or raw.get("Error Message")
                if msg and "feed" not in raw:
                    raise RuntimeError(str(msg))
                fresh = normalise_news(raw, set(watch))
            _news_cache.update(at=time.time(), key=key, items=fresh)
        except Exception as e:                                   # rate limit / outage: serve the last good copy
            if not _news_cache["items"]:
                return {**base, "data_mode": "none", "items": [], "stale": False,
                        "note": f"News provider unavailable right now ({str(e)[:140]})."}
            stale = True
    items = _news_cache["items"]
    if ticker:
        t = ticker.upper()
        items = [{**i, "sentiment": next(x["sentiment"] for x in i["tickers"] if x["ticker"] == t),
                  "score": next(x["score"] for x in i["tickers"] if x["ticker"] == t)}
                 for i in items if any(x["ticker"] == t for x in i["tickers"])]
    if sentiment:
        items = [i for i in items if i["sentiment"] == sentiment]
    items = sorted(items, key=lambda i: i["published_at"] or "", reverse=True)[:limit]
    return {**base, "data_mode": "live-data", "stale": stale,
            "fetched_at": datetime.fromtimestamp(_news_cache["at"], timezone.utc).isoformat(), "items": items}


class Watchlist(BaseModel):
    tickers: list[str]


@app.get("/api/v1/watchlist", response_model=Watchlist)
def get_watchlist():
    if WL_FILE.exists():
        return Watchlist(tickers=json.loads(WL_FILE.read_text()))
    return Watchlist(tickers=DEFAULT_WL)


@app.put("/api/v1/watchlist", response_model=Watchlist)
def put_watchlist(w: Watchlist):
    clean = []
    for t in w.tickers:
        t = t.strip().upper()
        if not re.fullmatch(r"[A-Z.\-]{1,6}", t):
            raise HTTPException(422, f"Invalid ticker: {t!r}")
        if t not in clean:
            clean.append(t)
    if len(clean) > 50:
        raise HTTPException(422, "Watchlist limited to 50 tickers")
    WL_FILE.parent.mkdir(parents=True, exist_ok=True)
    WL_FILE.write_text(json.dumps(clean))
    return Watchlist(tickers=clean)
