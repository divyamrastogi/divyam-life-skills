#!/usr/bin/env python3
"""Named, well-known trading strategies that each cast a vote.

Every strategy is a pure function ``f(df) -> pd.Series`` returning a vote in
{-1 (sell/short), 0 (hold/flat), +1 (buy/long)} for *every* bar, aligned to
``df.index``. Indicators use only backward-looking windows (rolling / ewm), so
the vote at bar *t* never peeks at the future.

This single representation drives both:
  • live signals  → ``series.iloc[-1]`` (today's vote)
  • backtests     → ``series.shift(1)`` (act on yesterday's vote, no lookahead)

Strategies are deliberately textbook so their behaviour is auditable:
  Trend-following : trend_sma, macd, donchian_breakout, adx_di, momentum, obv
  Mean-reversion  : rsi, bollinger, stochastic
"""

from __future__ import annotations

import pandas as pd

# ── Indicator primitives (return full Series) ────────────────────────────────

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def _bollinger(close: pd.Series, period: int = 20, k: float = 2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + k * std, mid, mid - k * std


def _stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    low_min = df["Low"].rolling(k_period).min()
    high_max = df["High"].rolling(k_period).max()
    k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    return k, k.rolling(d_period).mean()


def _adx(df: pd.DataFrame, period: int = 14):
    high, low, close = df["High"], df["Low"], df["Close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = ((up > down) & (up > 0)) * up.clip(lower=0)
    minus_dm = ((down > up) & (down > 0)) * down.clip(lower=0)
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx, plus_di, minus_di


def _obv(df: pd.DataFrame) -> pd.Series:
    direction = df["Close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * df["Volume"]).fillna(0).cumsum()


# ── Strategies (each returns a vote Series) ──────────────────────────────────

def trend_sma(df: pd.DataFrame) -> pd.Series:
    """Golden/Death cross — the canonical trend filter."""
    sma50 = df["Close"].rolling(50).mean()
    sma200 = df["Close"].rolling(200).mean()
    vote = pd.Series(0, index=df.index)
    vote[sma50 > sma200] = 1
    vote[sma50 < sma200] = -1
    return vote


def macd(df: pd.DataFrame) -> pd.Series:
    """MACD line above/below its signal line."""
    macd_line, signal_line, _ = _macd(df["Close"])
    vote = pd.Series(0, index=df.index)
    vote[macd_line > signal_line] = 1
    vote[macd_line < signal_line] = -1
    return vote


def rsi(df: pd.DataFrame) -> pd.Series:
    """RSI mean-reversion — buy oversold, sell overbought."""
    r = _rsi(df["Close"])
    vote = pd.Series(0, index=df.index)
    vote[r < 30] = 1
    vote[r > 70] = -1
    return vote


def bollinger(df: pd.DataFrame) -> pd.Series:
    """Bollinger band mean-reversion — buy below lower, sell above upper."""
    upper, _, lower = _bollinger(df["Close"])
    vote = pd.Series(0, index=df.index)
    vote[df["Close"] < lower] = 1
    vote[df["Close"] > upper] = -1
    return vote


def donchian_breakout(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Turtle-style channel breakout: long after a new N-day high, short after a
    new N-day low, holding the position until the opposite breakout."""
    prior_high = df["High"].rolling(period).max().shift(1)
    prior_low = df["Low"].rolling(period).min().shift(1)
    raw = pd.Series(float("nan"), index=df.index, dtype="float")
    raw[df["Close"] >= prior_high] = 1
    raw[df["Close"] <= prior_low] = -1
    return raw.ffill().fillna(0).astype(int)


def stochastic(df: pd.DataFrame) -> pd.Series:
    """Stochastic oscillator turning out of oversold / overbought."""
    k, d = _stochastic(df)
    vote = pd.Series(0, index=df.index)
    vote[(k < 20) & (k > d)] = 1
    vote[(k > 80) & (k < d)] = -1
    return vote


def adx_di(df: pd.DataFrame) -> pd.Series:
    """Directional movement: only act when ADX confirms a real trend (>25)."""
    adx, plus_di, minus_di = _adx(df)
    trending = adx > 25
    vote = pd.Series(0, index=df.index)
    vote[trending & (plus_di > minus_di)] = 1
    vote[trending & (minus_di > plus_di)] = -1
    return vote


def momentum(df: pd.DataFrame, lookback: int = 126) -> pd.Series:
    """Time-series momentum — 6-month rate of change (classic factor)."""
    roc = df["Close"].pct_change(lookback)
    vote = pd.Series(0, index=df.index)
    vote[roc > 0] = 1
    vote[roc < 0] = -1
    return vote


def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance-Volume vs its 20-day average — accumulation/distribution."""
    o = _obv(df)
    o_sma = o.rolling(20).mean()
    vote = pd.Series(0, index=df.index)
    vote[o > o_sma] = 1
    vote[o < o_sma] = -1
    return vote


# ── Registry ─────────────────────────────────────────────────────────────────

STRATEGIES: dict[str, dict] = {
    "trend_sma": {"fn": trend_sma, "kind": "trend", "label": "SMA 50/200 Trend"},
    "macd": {"fn": macd, "kind": "trend", "label": "MACD Momentum"},
    "donchian_breakout": {"fn": donchian_breakout, "kind": "trend", "label": "Donchian Breakout"},
    "adx_di": {"fn": adx_di, "kind": "trend", "label": "ADX Directional"},
    "momentum": {"fn": momentum, "kind": "trend", "label": "6-Month Momentum"},
    "obv": {"fn": obv, "kind": "trend", "label": "OBV Volume Trend"},
    "rsi": {"fn": rsi, "kind": "meanrev", "label": "RSI Mean-Reversion"},
    "bollinger": {"fn": bollinger, "kind": "meanrev", "label": "Bollinger Mean-Reversion"},
    "stochastic": {"fn": stochastic, "kind": "meanrev", "label": "Stochastic"},
}

# Minimum bars needed for the slowest strategy (SMA200 + momentum lookback).
MIN_BARS = 200


def compute_votes(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Run every strategy on *df*, returning {name: vote Series}."""
    out = {}
    for name, meta in STRATEGIES.items():
        try:
            out[name] = meta["fn"](df).reindex(df.index).fillna(0).astype(int)
        except Exception:
            out[name] = pd.Series(0, index=df.index, dtype=int)
    return out


def live_signals(df: pd.DataFrame) -> dict[str, int]:
    """Today's vote from each strategy (last bar)."""
    return {name: int(s.iloc[-1]) for name, s in compute_votes(df).items()}


def consensus(votes_last: dict[str, int]) -> dict:
    """Aggregate per-strategy votes into a consensus verdict.

    net    = sum of votes (range roughly -9..+9 with 9 strategies)
    Going with the *consensus of signals*: a clear majority one way drives the
    verdict; a split tape stays NEUTRAL.
    """
    net = sum(votes_last.values())
    n_buy = sum(1 for v in votes_last.values() if v > 0)
    n_sell = sum(1 for v in votes_last.values() if v < 0)
    n_hold = sum(1 for v in votes_last.values() if v == 0)

    if net >= 5:
        verdict, emoji = "STRONG BUY", "🟢🟢"
    elif net >= 2:
        verdict, emoji = "BUY", "🟢"
    elif net <= -5:
        verdict, emoji = "STRONG SELL", "🔴🔴"
    elif net <= -2:
        verdict, emoji = "SELL", "🔴"
    else:
        verdict, emoji = "NEUTRAL", "⚪"

    return {
        "net": net,
        "n_buy": n_buy,
        "n_sell": n_sell,
        "n_hold": n_hold,
        "n_total": len(votes_last),
        "verdict": verdict,
        "emoji": emoji,
    }
