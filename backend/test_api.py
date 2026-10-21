"""Run from the project folder:  python -m pytest backend -q"""
import importlib
import json
import os

import pandas as pd
from fastapi.testclient import TestClient


def client(project_dir):
    os.environ["PROJECT_DIR"] = str(project_dir)
    import backend.main as m
    importlib.reload(m)
    return TestClient(m.app), m


def test_demo_mode_is_labelled(tmp_path):
    c, _ = client(tmp_path)
    r = c.get("/api/v1/forecasts").json()
    assert r["data_mode"] == "demo" and "DEMO" in r["note"] and r["as_of"] is None
    assert c.get("/api/v1/candles/AAPL").json()["data_mode"] == "demo"
    assert c.get("/api/v1/tracking/summary").json()["items"] == []      # never fabricated
    assert c.get("/api/v1/health").json()["mode"] == "demo"


def test_live_data_and_validation(tmp_path):
    (tmp_path / "output/processed").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    pd.DataFrame({"Ticker": ["TSLA"], "recent_20d_vol_ann_pct": [30.0],
                  "forecast_5d_vol_ann_pct": [45.0], "forecast_vs_recent_pct": [50.0],
                  "typical_daily_move_pct": [2.8], "earnings_in_window": [True],
                  "next_earnings": ["2026-10-21"]}).to_csv(
        tmp_path / "output/processed/volatility_forecast.csv", index=False)
    d = pd.bdate_range("2025-01-01", periods=400)
    pd.DataFrame({"Date": d, "Open": 1.0, "High": 1.1, "Low": 0.9, "Close": 1.0, "Volume": 5,
                  "Ticker": "TSLA", "daily_return_pct": [0.1, -0.2] * 200}).to_csv(
        tmp_path / "data/stocks.csv", index=False)
    c, _ = client(tmp_path)
    f = c.get("/api/v1/forecasts").json()
    assert f["data_mode"] == "live-data" and f["items"][0]["earnings_in_window"] is True
    assert f["items"][0]["regime"] in {"Calm", "Normal", "Elevated", "High"}
    assert len(c.get("/api/v1/candles/TSLA?range=3M").json()["candles"]) == 63
    assert c.get("/api/v1/candles/ZZZZ").status_code == 404
    assert c.get("/api/v1/candles/TSLA?range=9Y").status_code == 422
    assert c.get("/api/v1/forecasts/TSLA").json()["ticker"] == "TSLA"


def test_watchlist_persists_and_validates(tmp_path):
    c, _ = client(tmp_path)
    assert c.put("/api/v1/watchlist", json={"tickers": ["aapl", "AAPL", "nvda"]}).json()["tickers"] == ["AAPL", "NVDA"]
    assert c.get("/api/v1/watchlist").json()["tickers"] == ["AAPL", "NVDA"]
    assert c.put("/api/v1/watchlist", json={"tickers": ["BAD TICKER!"]}).status_code == 422


def test_backtest_and_models_endpoints(tmp_path):
    (tmp_path / "output/processed").mkdir(parents=True)
    c, _ = client(tmp_path)
    assert c.get("/api/v1/backtest/sizing").json()["data_mode"] == "none"      # nothing invented
    assert c.get("/api/v1/models/by-stock").json()["items"] == []
    pd.DataFrame({"strategy": ["equal_weight"], "sharpe": [1.1]}).to_csv(
        tmp_path / "output/processed/position_sizing_results.csv", index=False)
    pd.DataFrame({"Date": ["2020-01-01", "2020-01-02"], "equal_weight": [1.0, 1.01]}).to_csv(
        tmp_path / "output/processed/position_sizing_equity.csv", index=False)
    j = c.get("/api/v1/backtest/sizing").json()
    assert j["data_mode"] == "live-data" and len(j["equity"]["equal_weight"]) == 2


def test_quotes_and_overview(tmp_path):
    c, _ = client(tmp_path)
    assert c.get("/api/v1/quotes").json()["data_mode"] == "none"
    assert c.get("/api/v1/overview").json()["data_mode"] == "none"
    (tmp_path / "output/processed").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    pd.DataFrame({"Ticker": ["TSLA"], "recent_20d_vol_ann_pct": [30.0], "forecast_5d_vol_ann_pct": [45.0],
                  "forecast_vs_recent_pct": [50.0], "typical_daily_move_pct": [2.8],
                  "earnings_in_window": [True]}).to_csv(tmp_path / "output/processed/volatility_forecast.csv", index=False)
    d = pd.bdate_range("2025-01-01", periods=300)
    rows = [pd.DataFrame({"Date": d, "Open": 1.0, "High": 1.1, "Low": 0.9, "Close": 2.0, "Volume": 5, "Ticker": t,
                          "Sector": s, "daily_return_pct": [0.5, -0.4] * 150}) for t, s in [("TSLA", "Consumer"), ("SPY", "Benchmark")]]
    pd.concat(rows).to_csv(tmp_path / "data/stocks.csv", index=False)
    c, _ = client(tmp_path)
    assert c.get("/api/v1/quotes").json()["items"][0]["close"] == 2.0
    o = c.get("/api/v1/overview").json()
    assert o["data_mode"] == "live-data" and o["sectors"][0]["sector"] == "Consumer" and o["spy_recent_vol_ann_pct"] > 0


def test_trend_is_descriptive_and_correct(tmp_path):
    (tmp_path / "data").mkdir()
    n = 300
    pd.DataFrame({"Date": pd.bdate_range("2025-01-01", periods=n), "Open": 1.0, "High": 1.0, "Low": 1.0,
                  "Close": [100 + i for i in range(n)], "Volume": 1, "Ticker": "UP",
                  "daily_return_pct": 0.1}).to_csv(tmp_path / "data/stocks.csv", index=False)
    c, _ = client(tmp_path)
    j = c.get("/api/v1/trend").json()
    assert j["items"][0]["label"] == "Uptrend" and j["items"][0]["off_52w_high_pct"] == 0.0
    assert "not a forecast" in j["note"]


def test_access_key_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCESS_KEY", "s3cret")
    c, _ = client(tmp_path)
    assert c.get("/api/v1/forecasts").status_code == 401
    assert c.get("/api/v1/forecasts", headers={"x-access-key": "wrong"}).status_code == 401
    assert c.get("/api/v1/forecasts", headers={"x-access-key": "s3cret"}).status_code == 200
    assert c.get("/api/v1/health").status_code == 200                  # health stays open
    monkeypatch.delenv("ACCESS_KEY")
    c, _ = client(tmp_path)
    assert c.get("/api/v1/forecasts").status_code == 200               # no key set = open (local use)


RAW_NEWS = {"feed": [
    {"title": "Apple beats", "url": "https://x.test/a", "source": "Wire", "time_published": "20260102T153000",
     "overall_sentiment_score": 0.31, "overall_sentiment_label": "Somewhat-Bullish",
     "ticker_sentiment": [{"ticker": "AAPL", "relevance_score": "0.9", "ticker_sentiment_score": "0.4", "ticker_sentiment_label": "Bullish"}]},
    {"title": "Chip supply worries", "url": "https://x.test/b", "source": "Daily", "time_published": "20260103T090000",
     "overall_sentiment_score": -0.3, "overall_sentiment_label": "Somewhat-Bearish",
     "ticker_sentiment": [{"ticker": "NVDA", "relevance_score": "0.8", "ticker_sentiment_score": "-0.35", "ticker_sentiment_label": "Somewhat-Bearish"},
                          {"ticker": "MSFT", "relevance_score": "0.1", "ticker_sentiment_score": "0.0", "ticker_sentiment_label": "Neutral"}]},
    {"title": "Unrelated company", "url": "https://x.test/c", "source": "Daily", "time_published": "20260103T100000",
     "overall_sentiment_score": 0.0, "overall_sentiment_label": "Neutral",
     "ticker_sentiment": [{"ticker": "ZZZZ", "relevance_score": "0.9", "ticker_sentiment_score": "0", "ticker_sentiment_label": "Neutral"}]}]}


def test_news_none_without_key_and_normalised_with_key(tmp_path, monkeypatch):
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    c, _ = client(tmp_path)
    j = c.get("/api/v1/news").json()
    assert j["data_mode"] == "none" and j["items"] == [] and "FINNHUB_API_KEY" in j["note"]      # never invented
    monkeypatch.setenv("NEWS_API_KEY", "k")
    c, m = client(tmp_path)
    monkeypatch.setattr(m, "av_fetch", lambda key: RAW_NEWS)
    j = c.get("/api/v1/news").json()
    titles = [i["title"] for i in j["items"]]
    assert titles == ["Chip supply worries", "Apple beats"]                    # newest first; irrelevant + low-relevance dropped
    assert j["items"][0]["tickers"] == [{"ticker": "NVDA", "sentiment": "Negative", "score": -0.35}]
    assert j["items"][1]["sentiment"] == "Positive" and j["items"][1]["published_at"].startswith("2026-01-02T15:30")
    assert [i["title"] for i in c.get("/api/v1/news?ticker=aapl").json()["items"]] == ["Apple beats"]
    assert [i["title"] for i in c.get("/api/v1/news?sentiment=Negative").json()["items"]] == ["Chip supply worries"]
    assert c.get("/api/v1/news?sentiment=Bogus").status_code == 422


def test_news_rate_limit_serves_stale_copy(tmp_path, monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setenv("NEWS_API_KEY", "k")
    c, m = client(tmp_path)
    monkeypatch.setattr(m, "av_fetch", lambda key: RAW_NEWS)
    assert len(c.get("/api/v1/news").json()["items"]) == 2
    m._news_cache["at"] = 0                                                    # expire the cache
    monkeypatch.setattr(m, "av_fetch", lambda key: {"Information": "rate limit reached"})
    j = c.get("/api/v1/news").json()
    assert j["stale"] is True and len(j["items"]) == 2


def test_finnhub_news_merged_toned_and_ordered(tmp_path, monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "k")
    c, m = client(tmp_path)
    same = {"headline": "Apple stock surges after strong results", "url": "https://x.test/1", "source": "Wire", "datetime": 1767367800}
    fake = {"AAPL": [same, {"headline": "Lawsuit risk grows for Apple", "url": "https://x.test/2", "source": "Daily", "datetime": 1767454200}],
            "MSFT": [same, {"headline": "Microsoft holds event", "url": "", "source": "Daily", "datetime": 1}]}   # no url -> dropped
    monkeypatch.setattr(m, "finnhub_fetch", lambda key, syms: fake)
    j = c.get("/api/v1/news").json()
    assert j["source"] == "Finnhub company news" and "keyword estimate" in j["note"]
    assert [i["title"] for i in j["items"]] == ["Lawsuit risk grows for Apple", "Apple stock surges after strong results"]
    top = {i["title"]: i for i in j["items"]}
    assert top["Apple stock surges after strong results"]["sentiment"] == "Positive"
    assert sorted(t["ticker"] for t in top["Apple stock surges after strong results"]["tickers"]) == ["AAPL", "MSFT"]   # merged, no duplicate
    assert top["Lawsuit risk grows for Apple"]["sentiment"] == "Negative"
    assert top["Apple stock surges after strong results"]["published_at"].startswith("2026-01-02")
    assert [i["title"] for i in c.get("/api/v1/news?ticker=MSFT").json()["items"]] == ["Apple stock surges after strong results"]
