# Data sources and zero-cost policy

Quantum AI runs with **no paid services**. Everything below is either free, open-source, or documented-only.
This matrix is generated from `backend/sources.py` and shown in the app under Settings, so the two never disagree.

| Source | Assets | Key | Free limits | Freshness | Redistribution | Status in app |
|---|---|---|---|---|---|---|
| **Yahoo Finance via yfinance** | Stocks, ETFs, indices, forex, futures (daily) | None | Unofficial; can rate-limit or block | End-of-day (previous close) | No | Used for prices and earnings dates (private use only) |
| **Finnhub company news** | Company news headlines | Free key (FINNHUB_API_KEY) | Free plan includes company news; about 60 calls/min (check current plan page) | Near real-time headlines | Unverified | Used for news (headline + link only) |
| **Alpha Vantage** | Stocks, forex, commodities | Free key | 25 requests/day, 5/min; free daily history limited to the latest 100 points; news and adjusted daily series are premium | End-of-day | No (free tier) | Documented only (not required) |
| **Marketaux news** | Financial news with entity sentiment | Free key | 100 requests/day and 3 articles per request on the free plan | Near real-time | Unverified | Documented only (too few articles per call) |
| **Frankfurter API (CBK rates)** | KES exchange rates (indicative) | None | Free, open-source API; be gentle (we cache 6h) | Daily CBK indicative rates | Unverified | Used for the Kenya shilling card (parser not yet verified live) |
| **Central Bank of Kenya publications** | Policy rate, T-bill rates, inflation, exchange rates | None | Published as web pages/PDFs, no official API | Daily/weekly/monthly | Link-out only | Link-out recommended |
| **Kenya National Bureau of Statistics** | CPI, GDP, trade statistics | None | Published reports and datasets | Monthly/quarterly | Unverified | Link-out recommended |
| **Nairobi Securities Exchange (official)** | NSE prices, announcements | Licence/request | Third-party distribution (incl. web apps) needs an NSE licence; historical end-of-day reports are sold on request | End-of-day | No (licence required) | Not used; link to NSE announcements only |
| **NSE-licensed vendors (Abacus, Synergy, GTN, Bloomberg...)** | NSE data | Paid | Paid | Real-time/delayed | Per contract | Excluded (zero-cost rule) |
| **NewsAPI.org** | General news | Free developer key | Developer plan is for development only, not production | Delayed | No | Excluded |
| **Kenyan news RSS feeds** | Headlines + links | None | Per publisher | Near real-time | Headline + link | Planned (not built yet) |
| **Local computation (pandas, scikit-learn)** | Indicators, volatility forecasts, backtests, rule-based summaries | None | Runs on our own servers | As fresh as the input data | Yes (our own calculations) | Used |

## Terms notes (read before going public or charging anyone)
- **Private tool vs public product.** Yahoo/yfinance prices and any free-tier API key are fine for a private, personal dashboard behind an access key. They are **not** licensed for a public or paid product. Before launching publicly, replace price data with a source that permits redistribution.
- **NSE (Kenya).** The NSE requires a distribution licence for third parties that pass its data on, including web apps. Until you have one, the Kenya section should show NSE announcements as links, economic data (CBK, KNBS) with attribution, and education, not NSE prices.
- **Alpha Vantage.** The free key allows 25 requests/day (5/min). Free daily history is limited to the latest 100 points, and the news and adjusted-daily endpoints are premium. Commodity endpoints exist but their free status was not confirmed, so none are used.
- **Marketaux.** The free plan allows 100 requests/day with 3 articles per request, which is too thin to rely on.
- **Not guaranteed free forever.** A free tier can change or end. Every integration degrades to an "unavailable" state; none falls back to invented numbers.

## Data labels in the app
Each response states its frequency (`end-of-day`, `simulated`, ...) and source. Prices here are **end-of-day** values. Nothing is real-time, and demo data is labelled `simulated`.

## Local calculations (free, no restrictions)
RSI(14), MACD(12,26,9), Bollinger(20,2), ATR(14) and SMAs are computed in `backend/indicators.py` with pandas. Volatility forecasts use the existing ensemble and are evaluated with chronological walk-forward tests and live tracking. News summaries are rule-based (counts and keyword tone), with no AI service.

## Still to verify or build
- Check the live response of the CBK/Frankfurter feed (open `/api/v1/fx/kes/raw`) and confirm the parser.
- Add permitted Kenyan RSS feeds (headline + link only) after checking each publisher's terms.
- Confirm Finnhub's free-plan terms for your intended use.
