"""Technical indicators computed locally with pandas (no paid service, no extra dependency).

Descriptive only: they summarise past prices and are not trading signals.
  RSI(14)        Wilder smoothing: 100 - 100 / (1 + avg_gain / avg_loss)
  MACD(12,26,9)  EMA12 - EMA26, signal = EMA9 of MACD, histogram = MACD - signal
  Bollinger(20)  SMA20 +/- 2 population standard deviations; %B = (close - lower) / (upper - lower)
  ATR(14)        Wilder average of the true range (max of H-L, |H-prevC|, |L-prevC|)
  SMA 20/50/200  simple moving averages of the close
Inputs: daily close, high and low prices (at least 60 days).
"""
import pandas as pd


def compute(close: pd.Series, high: pd.Series, low: pd.Series) -> dict:
    d = close.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    a_up = up.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    a_dn = dn.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi = 100 - 100 / (1 + a_up / a_dn.where(a_dn > 0))
    rsi = rsi.where(a_dn > 0, other=100.0).where(a_up.notna())
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    sma20 = close.rolling(20).mean()
    sd = close.rolling(20).std(ddof=0)
    upper, lower = sma20 + 2 * sd, sma20 - 2 * sd
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    last = lambda s: None if pd.isna(s.iloc[-1]) else round(float(s.iloc[-1]), 4)
    width = float(upper.iloc[-1] - lower.iloc[-1])
    pct_b = None if pd.isna(width) or width == 0 else round(float((close.iloc[-1] - lower.iloc[-1]) / width), 3)
    r = last(rsi)
    return {
        "rsi14": r,
        "rsi_zone": None if r is None else "Overbought zone (>70)" if r > 70 else "Oversold zone (<30)" if r < 30 else "Neutral zone",
        "macd": last(macd), "macd_signal": last(signal), "macd_hist": last(macd - signal),
        "macd_state": "MACD above its signal line" if (macd - signal).iloc[-1] > 0 else "MACD below its signal line",
        "bollinger_pct_b": pct_b,
        "bollinger_state": None if pct_b is None else "Near/above upper band" if pct_b >= 0.9 else "Near/below lower band" if pct_b <= 0.1 else "Inside the bands",
        "atr14": last(atr), "atr14_pct_of_price": None if pd.isna(atr.iloc[-1]) else round(float(atr.iloc[-1] / close.iloc[-1] * 100), 2),
        "sma20": last(sma20), "sma50": last(close.rolling(50).mean()), "sma200": last(close.rolling(200).mean()),
    }
