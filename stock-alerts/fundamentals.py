#!/usr/bin/env python3
"""Programmatic fundamental analysis via Yahoo Finance.

Pulls the headline value/quality/health metrics from ``yf.Ticker(t).info`` and
scores each 🟢 / 🟡 / 🔴 against sector-agnostic thresholds, then rolls them up
into a single fundamental grade that can be combined with the technical
consensus. For a deeper qualitative dive (Reddit sentiment, earnings-quality
red flags) use the separate ``stock-analyst`` skill.

Thresholds are intentionally broad rules of thumb — a 🔴 on a hyper-growth name
isn't automatically a sell, it's a flag to read the note next to it.
"""

from __future__ import annotations

import warnings

import yfinance as yf

warnings.filterwarnings("ignore")

GREEN, YELLOW, RED = "🟢", "🟡", "🔴"


def _grade(value, good, ok, higher_better=True):
    """Return (emoji, score) where score is +1/0/-1.

    ``good`` and ``ok`` are the green and yellow cutoffs. With
    ``higher_better`` the metric is graded value>=good → green, value>=ok →
    yellow, else red (and inverted when lower is better).
    """
    if value is None:
        return "▫️", None
    if higher_better:
        if value >= good:
            return GREEN, 1
        if value >= ok:
            return YELLOW, 0
        return RED, -1
    else:
        if value <= good:
            return GREEN, 1
        if value <= ok:
            return YELLOW, 0
        return RED, -1


def _pct(v):
    return None if v is None else v * 100


def analyze_fundamentals(ticker: str) -> dict:
    """Build a scored fundamental report for *ticker*."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:
        return {"ticker": ticker, "error": f"could not fetch fundamentals: {e}"}

    if not info.get("regularMarketPrice") and not info.get("currentPrice") and not info.get("previousClose"):
        return {"ticker": ticker, "error": "no fundamental data available"}

    name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector") or "—"
    industry = info.get("industry") or "—"

    fwd_pe = info.get("forwardPE")
    pb = info.get("priceToBook")
    peg = info.get("trailingPegRatio") or info.get("pegRatio")
    net_margin = _pct(info.get("profitMargins"))
    op_margin = _pct(info.get("operatingMargins"))
    roe = _pct(info.get("returnOnEquity"))
    d_e = info.get("debtToEquity")  # already a percentage in yfinance
    current_ratio = info.get("currentRatio")
    rev_growth = _pct(info.get("revenueGrowth"))
    fcf = info.get("freeCashflow")

    rows = []  # (category, label, display, emoji, score, note)

    def add(cat, label, value, display, good, ok, higher_better, note):
        emoji, score = _grade(value, good, ok, higher_better)
        rows.append((cat, label, display, emoji, score, note))

    # Valuation
    add("Valuation", "Forward P/E", fwd_pe,
        f"{fwd_pe:.1f}x" if fwd_pe else "N/A", 15, 30, False, "earnings vs price")
    add("Valuation", "Price/Book", pb,
        f"{pb:.1f}x" if pb else "N/A", 3, 8, False, "<1 = below book value")
    add("Valuation", "PEG", peg,
        f"{peg:.2f}" if peg else "N/A", 1.0, 2.0, False, "growth-adjusted value")
    # Profitability
    add("Profitability", "Net Margin", net_margin,
        f"{net_margin:.1f}%" if net_margin is not None else "N/A", 15, 5, True, "bottom-line efficiency")
    add("Profitability", "Operating Margin", op_margin,
        f"{op_margin:.1f}%" if op_margin is not None else "N/A", 15, 5, True, "core business")
    add("Profitability", "ROE", roe,
        f"{roe:.1f}%" if roe is not None else "N/A", 15, 5, True, "capital allocation")
    # Health
    add("Balance Sheet", "Debt/Equity", d_e,
        f"{d_e:.0f}%" if d_e is not None else "N/A", 50, 150, False, "leverage")
    add("Balance Sheet", "Current Ratio", current_ratio,
        f"{current_ratio:.2f}" if current_ratio else "N/A", 1.5, 1.0, True, "short-term solvency")
    # Growth
    add("Growth", "Revenue Growth", rev_growth,
        f"{rev_growth:.1f}%" if rev_growth is not None else "N/A", 15, 5, True, "YoY")
    add("Growth", "Free Cash Flow", fcf,
        (f"${fcf/1e9:.2f}B" if fcf else "N/A"), 1, 0, True, "cash is real")

    scored = [r[4] for r in rows if r[4] is not None]
    ratio = sum(scored) / len(scored) if scored else 0.0
    if ratio > 0.4:
        grade, grade_emoji = "STRONG", GREEN
    elif ratio >= -0.1:
        grade, grade_emoji = "MIXED", YELLOW
    else:
        grade, grade_emoji = "WEAK", RED

    return {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "industry": industry,
        "rows": rows,
        "score_ratio": ratio,
        "grade": grade,
        "grade_emoji": grade_emoji,
        "n_green": sum(1 for r in rows if r[3] == GREEN),
        "n_red": sum(1 for r in rows if r[3] == RED),
    }


def format_fundamentals(rep: dict) -> str:
    if "error" in rep:
        return f"❌ {rep['ticker']}: {rep['error']}"
    lines = [
        f"📋 *{rep['name']}* ({rep['ticker']}) — Fundamentals",
        f"Sector: {rep['sector']} · {rep['industry']}",
        f"Grade: {rep['grade_emoji']} {rep['grade']}  ({rep['n_green']}🟢 / {rep['n_red']}🔴)",
        "",
    ]
    last_cat = None
    for cat, label, display, emoji, _score, note in rep["rows"]:
        if cat != last_cat:
            lines.append(f"*{cat}*")
            last_cat = cat
        lines.append(f"  {emoji} {label}: {display}  — {note}")
    lines.append("")
    lines.append("_Not financial advice. Do your own research._")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    for t in sys.argv[1:] or ["AAPL"]:
        print(format_fundamentals(analyze_fundamentals(t.upper())))
        print()
