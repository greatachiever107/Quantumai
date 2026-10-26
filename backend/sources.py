"""Data-source matrix shown on the Settings page and documented in docs/DATA_SOURCES.md."""
SOURCES = [
 {
  "id": "yfinance",
  "name": "Yahoo Finance via yfinance",
  "assets": "Stocks, ETFs, indices, forex, futures (daily)",
  "key": "None",
  "limits": "Unofficial; can rate-limit or block",
  "freshness": "End-of-day (previous close)",
  "terms": "yfinance documents its data as for personal/research use; not licensed for public or paid redistribution",
  "redistribution": "No",
  "status": "Used for prices and earnings dates (private use only)"
 },
 {
  "id": "finnhub",
  "name": "Finnhub company news",
  "assets": "Company news headlines",
  "key": "Free key (FINNHUB_API_KEY)",
  "limits": "Free plan includes company news; about 60 calls/min (check current plan page)",
  "freshness": "Near real-time headlines",
  "terms": "Free plan is for personal use; commercial display needs checking",
  "redistribution": "Unverified",
  "status": "Used for news (headline + link only)"
 },
 {
  "id": "alphavantage",
  "name": "Alpha Vantage",
  "assets": "Stocks, forex, commodities",
  "key": "Free key",
  "limits": "25 requests/day, 5/min; free daily history limited to the latest 100 points; news and adjusted daily series are premium",
  "freshness": "End-of-day",
  "terms": "Free key is personal use; commercial needs a paid plan",
  "redistribution": "No (free tier)",
  "status": "Documented only (not required)"
 },
 {
  "id": "marketaux",
  "name": "Marketaux news",
  "assets": "Financial news with entity sentiment",
  "key": "Free key",
  "limits": "100 requests/day and 3 articles per request on the free plan",
  "freshness": "Near real-time",
  "terms": "Free-plan display terms unverified",
  "redistribution": "Unverified",
  "status": "Documented only (too few articles per call)"
 },
 {
  "id": "frankfurter_cbk",
  "name": "Frankfurter API (CBK rates)",
  "assets": "KES exchange rates (indicative)",
  "key": "None",
  "limits": "Free, open-source API; be gentle (we cache 6h)",
  "freshness": "Daily CBK indicative rates",
  "terms": "Source is the Central Bank of Kenya; attribute CBK and Frankfurter",
  "redistribution": "Unverified",
  "status": "Used for the Kenya shilling card (cross-rates computed from the EUR-based feed)"
 },
 {
  "id": "cbk",
  "name": "Central Bank of Kenya publications",
  "assets": "Policy rate, T-bill rates, inflation, exchange rates",
  "key": "None",
  "limits": "Published as web pages/PDFs, no official API",
  "freshness": "Daily/weekly/monthly",
  "terms": "Official; link out and attribute unless permission is obtained",
  "redistribution": "Link-out only",
  "status": "Link-out recommended"
 },
 {
  "id": "knbs",
  "name": "Kenya National Bureau of Statistics",
  "assets": "CPI, GDP, trade statistics",
  "key": "None",
  "limits": "Published reports and datasets",
  "freshness": "Monthly/quarterly",
  "terms": "Check KNBS data-use terms before reusing",
  "redistribution": "Unverified",
  "status": "Link-out recommended"
 },
 {
  "id": "nse",
  "name": "Nairobi Securities Exchange (official)",
  "assets": "NSE prices, announcements",
  "key": "Licence/request",
  "limits": "Third-party distribution (incl. web apps) needs an NSE licence; historical end-of-day reports are sold on request",
  "freshness": "End-of-day",
  "terms": "Licensed distribution only",
  "redistribution": "No (licence required)",
  "status": "Not used; link to NSE announcements only"
 },
 {
  "id": "nse_vendors",
  "name": "NSE-licensed vendors (Abacus, Synergy, GTN, Bloomberg...)",
  "assets": "NSE data",
  "key": "Paid",
  "limits": "Paid",
  "freshness": "Real-time/delayed",
  "terms": "Commercial",
  "redistribution": "Per contract",
  "status": "Excluded (zero-cost rule)"
 },
 {
  "id": "newsapi",
  "name": "NewsAPI.org",
  "assets": "General news",
  "key": "Free developer key",
  "limits": "Developer plan is for development only, not production",
  "freshness": "Delayed",
  "terms": "Not for production use",
  "redistribution": "No",
  "status": "Excluded"
 },
 {
  "id": "rss",
  "name": "Kenyan news RSS feeds",
  "assets": "Headlines + links",
  "key": "None",
  "limits": "Per publisher",
  "freshness": "Near real-time",
  "terms": "Each publisher sets its own terms; use headline + link only",
  "redistribution": "Headline + link",
  "status": "Planned (not built yet)"
 },
 {
  "id": "local",
  "name": "Local computation (pandas, scikit-learn)",
  "assets": "Indicators, volatility forecasts, backtests, rule-based summaries",
  "key": "None",
  "limits": "Runs on our own servers",
  "freshness": "As fresh as the input data",
  "terms": "Open-source licences",
  "redistribution": "Yes (our own calculations)",
  "status": "Used"
 }
]
