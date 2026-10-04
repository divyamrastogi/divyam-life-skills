#!/usr/bin/env python3
"""Stock Technical Analysis Alert Engine.

Fetches OHLCV data from Yahoo Finance, computes 10 technical indicators,
generates buy/sell/neutral signals, and outputs a summary.
"""

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Indicators ──────────────────────────────────────────────────────────────

def compute_rsi(df, period=14):
    """RSI — overbought >70, oversold <30."""
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0.0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def compute_macd(df):
    """MACD — returns (macd_line, signal_line, histogram)."""
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line.iloc[-1], signal_line.iloc[-1], hist.iloc[-1]


def compute_bollinger(df, period=20, std_dev=2):
    """Bollinger Bands — price near upper = overbought, near lower = oversold."""
    sma = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    price = df["Close"].iloc[-1]
    return upper.iloc[-1], sma.iloc[-1], lower.iloc[-1], price


def compute_sma_ema(df):
    """SMA/EMA 50 & 200 — trend direction + golden/death cross."""
    sma50 = df["Close"].rolling(window=50).mean().iloc[-1]
    sma200 = df["Close"].rolling(window=200).mean().iloc[-1]
    ema50 = df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = df["Close"].ewm(span=200, adjust=False).mean().iloc[-1]
    return sma50, sma200, ema50, ema200


def compute_stochastic(df, k_period=14, d_period=3):
    """Stochastic Oscillator — %K and %D."""
    low_min = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    return k.iloc[-1], d.iloc[-1]


def compute_adx(df, period=14):
    """ADX — trend strength (>25 = trending)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    return adx.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]


def compute_atr(df, period=14):
    """ATR — volatility measure."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1]


def compute_obv(df):
    """On Balance Volume — volume pressure."""
    obv = (pd.Series(
        [0] * len(df), index=df.index
    )).astype(float)
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + df["Volume"].iloc[i]
        elif df["Close"].iloc[i] < df["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - df["Volume"].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]
    # Compare 20-day OBV trend
    obv_sma = obv.rolling(window=20).mean()
    return obv.iloc[-1], obv_sma.iloc[-1]


def compute_vwap(df):
    """VWAP — intraday value benchmark (daily approximation)."""
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vwap = (typical * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return vwap.iloc[-1]


def compute_fibonacci(df, lookback=90):
    """Fibonacci Retracement — key support/resistance levels."""
    recent = df.tail(lookback)
    high = recent["High"].max()
    low = recent["Low"].min()
    diff = high - low
    levels = {
        "0.0": round(high, 2),
        "0.236": round(high - 0.236 * diff, 2),
        "0.382": round(high - 0.382 * diff, 2),
        "0.5": round(high - 0.5 * diff, 2),
        "0.618": round(high - 0.618 * diff, 2),
        "0.786": round(high - 0.786 * diff, 2),
        "1.0": round(low, 2),
    }
    price = df["Close"].iloc[-1]
    # Find nearest level
    closest = min(levels.keys(), key=lambda k: abs(levels[k] - price))
    return levels, closest


# ── Signal Generation ───────────────────────────────────────────────────────

def analyze_stock(ticker: str) -> dict:
    """Run all 10 indicators on a stock and return signals."""
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y", interval="1d")

    if df.empty or len(df) < 200:
        return {"error": f"Not enough data for {ticker} (got {len(df)} bars, need 200+)"}

    price = round(df["Close"].iloc[-1], 2)
    prev_close = round(df["Close"].iloc[-2], 2)
    change_pct = round((price - prev_close) / prev_close * 100, 2)

    signals = []
    score = 0  # -10 to +10

    # 1. RSI
    try:
        rsi = compute_rsi(df)
        if rsi < 30:
            sig = "🟢 OVERSOLD"
            score += 2
        elif rsi > 70:
            sig = "🔴 OVERBOUGHT"
            score -= 2
        else:
            sig = "⚪ Neutral"
        signals.append(("RSI (14)", f"{rsi:.1f}", sig))
    except Exception as e:
        signals.append(("RSI (14)", "ERR", str(e)))

    # 2. MACD
    try:
        macd, signal, hist = compute_macd(df)
        if hist > 0 and hist > df["Close"].iloc[-1] * 0.001:
            sig = "🟢 Bullish"
            score += 2
        elif hist < 0:
            sig = "🔴 Bearish"
            score -= 2
        else:
            sig = "⚪ Flat"
        signals.append(("MACD", f"MACD:{macd:.2f} Sig:{signal:.2f}", sig))
    except Exception as e:
        signals.append(("MACD", "ERR", str(e)))

    # 3. Bollinger Bands
    try:
        upper, mid, lower, p = compute_bollinger(df)
        bb_width = (upper - lower) / mid * 100
        if p > upper:
            sig = "🔴 Above Upper Band"
            score -= 1
        elif p < lower:
            sig = "🟢 Below Lower Band"
            score += 1
        else:
            sig = "⚪ Within Bands"
        signals.append(("Bollinger", f"U:{upper:.2f} L:{lower:.2f}", sig))
    except Exception as e:
        signals.append(("Bollinger", "ERR", str(e)))

    # 4. SMA/EMA Crossover
    try:
        sma50, sma200, ema50, ema200 = compute_sma_ema(df)
        if sma50 > sma200 and price > sma50:
            sig = "🟢 Golden Cross + Above SMA50"
            score += 2
        elif sma50 < sma200:
            sig = "🔴 Death Cross"
            score -= 2
        else:
            sig = "⚪ Mixed"
        signals.append(("SMA 50/200", f"50:{sma50:.2f} 200:{sma200:.2f}", sig))
    except Exception as e:
        signals.append(("SMA 50/200", "ERR", str(e)))

    # 5. Stochastic
    try:
        k, d = compute_stochastic(df)
        if k < 20 and d < 20:
            sig = "🟢 Oversold"
            score += 1
        elif k > 80 and d > 80:
            sig = "🔴 Overbought"
            score -= 1
        elif k > d:
            sig = "🟢 %K > %D"
            score += 1
        else:
            sig = "🔴 %K < %D"
            score -= 1
        signals.append(("Stochastic", f"%K:{k:.1f} %D:{d:.1f}", sig))
    except Exception as e:
        signals.append(("Stochastic", "ERR", str(e)))

    # 6. ADX
    try:
        adx, plus_di, minus_di = compute_adx(df)
        if adx > 25:
            trend = "Strong Trend"
            if plus_di > minus_di:
                sig = f"🟢 {trend} (Bullish)"
                score += 2
            else:
                sig = f"🔴 {trend} (Bearish)"
                score -= 2
        else:
            sig = "⚪ Weak/No Trend"
        signals.append(("ADX (14)", f"ADX:{adx:.1f} +DI:{plus_di:.1f} -DI:{minus_di:.1f}", sig))
    except Exception as e:
        signals.append(("ADX", "ERR", str(e)))

    # 7. ATR
    try:
        atr = compute_atr(df)
        atr_pct = atr / price * 100
        if atr_pct > 3:
            sig = "⚠️ High Volatility"
        elif atr_pct < 1:
            sig = "✅ Low Volatility"
        else:
            sig = "⚪ Normal"
        signals.append(("ATR (14)", f"{atr:.2f} ({atr_pct:.1f}%)", sig))
    except Exception as e:
        signals.append(("ATR", "ERR", str(e)))

    # 8. OBV
    try:
        obv, obv_sma = compute_obv(df)
        if obv > obv_sma:
            sig = "🟢 Accumulation (buying pressure)"
            score += 1
        else:
            sig = "🔴 Distribution (selling pressure)"
            score -= 1
        signals.append(("OBV", f"{obv/1e6:.1f}M", sig))
    except Exception as e:
        signals.append(("OBV", "ERR", str(e)))

    # 9. VWAP
    try:
        vwap = compute_vwap(df)
        if price > vwap:
            sig = "🟢 Above VWAP (bullish)"
            score += 1
        else:
            sig = "🔴 Below VWAP (bearish)"
            score -= 1
        signals.append(("VWAP", f"{vwap:.2f}", sig))
    except Exception as e:
        signals.append(("VWAP", "ERR", str(e)))

    # 10. Fibonacci
    try:
        fib_levels, closest = compute_fibonacci(df)
        level_price = fib_levels[closest]
        # Check if near support (lower levels) or resistance (upper levels)
        level_num = float(closest)
        if level_num >= 0.618:
            sig = f"🟢 Near Support ({closest}: {level_price})"
            score += 1
        elif level_num <= 0.382:
            sig = f"🔴 Near Resistance ({closest}: {level_price})"
            score -= 1
        else:
            sig = f"⚪ Mid-Range ({closest}: {level_price})"
        signals.append(("Fibonacci", f"Nearest: {closest}", sig))
    except Exception as e:
        signals.append(("Fibonacci", "ERR", str(e)))

    # Overall verdict
    if score >= 5:
        verdict = "🟢🟢 STRONG BUY"
    elif score >= 2:
        verdict = "🟢 BUY"
    elif score <= -5:
        verdict = "🔴🔴 STRONG SELL"
    elif score <= -2:
        verdict = "🔴 SELL"
    else:
        verdict = "⚪ NEUTRAL"

    return {
        "ticker": ticker,
        "price": price,
        "change_pct": change_pct,
        "score": score,
        "verdict": verdict,
        "signals": signals,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def format_report(result: dict) -> str:
    """Format analysis as WhatsApp-friendly message."""
    if "error" in result:
        return f"❌ {result['error']}"

    lines = [
        f"📊 *{result['ticker']}* — ${result['price']} ({result['change_pct']:+.2f}%)",
        f"Verdict: {result['verdict']} (score: {result['score']}/10)",
        "",
    ]

    for name, value, signal in result["signals"]:
        lines.append(f"• *{name}*: {value}")
        lines.append(f"  {signal}")

    lines.append("")
    lines.append(f"🕐 {result['timestamp']}")
    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Read from central watchlist
    watchlist_path = Path("~/clawd/memory/watchlist.md").expanduser()

    if len(sys.argv) > 1:
        tickers = sys.argv[1:]
    else:
        if not watchlist_path.exists():
            print(f"Watchlist not found at {watchlist_path}")
            sys.exit(1)

        # Parse tickers from ALL markdown tables in watchlist (dedup)
        tickers = []
        seen = set()
        in_table = False
        with open(watchlist_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("| Ticker"):
                    in_table = True
                elif in_table and line.startswith("|"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and parts[0] == "":
                        ticker = parts[1].strip()
                        if ticker and ticker != "Ticker" and not ticker.startswith("-") and ticker not in seen:
                            tickers.append(ticker)
                            seen.add(ticker)
                    elif in_table and not line.startswith("|"):
                        in_table = False  # continue scanning for more tables

    if not tickers:
        print("No stocks in watchlist. Add tickers to watchlist.json or pass as args.")
        sys.exit(1)

    reports = []
    for ticker in tickers:
        result = analyze_stock(ticker.upper())
        reports.append(format_report(result))

    print("\n\n".join(reports))
