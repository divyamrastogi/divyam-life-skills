#!/usr/bin/env python3
"""Shared helpers for the trader engine.

- Ticker loading from the central watchlist.md and holdings.md
- Cached OHLCV history fetch from Yahoo Finance (free)

Both watchlist.md and holdings.md are markdown tables. holdings.md uses a
separate "LSE Stocks" section where tickers are written WITHOUT the ``.L``
suffix that Yahoo Finance requires, so we re-attach it for that section.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

TRADER_DIR = Path("~/clawd/trader-analyst").expanduser()
WATCHLIST_PATH = TRADER_DIR / "watchlist.md"
HOLDINGS_PATH = TRADER_DIR / "holdings.md"

# Yahoo Finance symbols for LSE tickers that are listed bare in holdings.md.
_LSE_SUFFIX = ".L"


# ── Markdown table parsing ───────────────────────────────────────────────────

def _parse_markdown_tickers(path: Path, lse_sections=None) -> list[str]:
    """Extract tickers from the first column of every markdown table in *path*.

    ``lse_sections`` is a set of lowercased ``##`` heading substrings under which
    bare tickers should get the ``.L`` suffix appended (for holdings.md).
    """
    lse_sections = lse_sections or set()
    tickers: list[str] = []
    if not path.exists():
        return tickers

    in_lse = False
    for raw in path.read_text().splitlines():
        line = raw.strip()

        # Track section headings to know when we're in an LSE block.
        if line.startswith("#"):
            heading = line.lstrip("#").strip().lower()
            in_lse = any(s in heading for s in lse_sections)
            continue

        if not line.startswith("|"):
            continue

        parts = [p.strip() for p in line.split("|")]
        # A markdown row splits to ['', col1, col2, ..., ''].
        if len(parts) < 3:
            continue
        cell = parts[1]

        # Skip header + separator rows.
        if not cell or cell.lower() in {"ticker", "symbol"} or set(cell) <= set("-: "):
            continue

        sym = cell.upper()
        if in_lse and not sym.endswith(_LSE_SUFFIX):
            sym = sym + _LSE_SUFFIX
        if sym not in tickers:
            tickers.append(sym)

    return tickers


def load_watchlist() -> list[str]:
    """Tickers from the central watchlist.md (single source of truth)."""
    return _parse_markdown_tickers(WATCHLIST_PATH)


def load_holdings() -> list[str]:
    """Tickers the user actually owns, from holdings.md."""
    return _parse_markdown_tickers(HOLDINGS_PATH, lse_sections={"lse"})


# ── Data fetch (cached per-process) ──────────────────────────────────────────

_HISTORY_CACHE: dict[tuple[str, str], pd.DataFrame] = {}


def fetch_history(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Download OHLCV history, cached per (ticker, period) for this process.

    Returns an empty DataFrame on failure rather than raising, so callers can
    skip bad tickers gracefully.
    """
    key = (ticker.upper(), period)
    if key in _HISTORY_CACHE:
        return _HISTORY_CACHE[key]

    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
    except Exception:
        df = pd.DataFrame()

    # Normalise: drop rows with no close, ensure required columns exist.
    if not df.empty:
        df = df.dropna(subset=["Close"])
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col not in df.columns:
                df[col] = pd.NA

    _HISTORY_CACHE[key] = df
    return df


# ── Display helpers ──────────────────────────────────────────────────────────

def currency_symbol(ticker: str) -> str:
    return "£" if ticker.upper().endswith(_LSE_SUFFIX) else "$"
