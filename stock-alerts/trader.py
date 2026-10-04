#!/usr/bin/env python3
"""Trader — unified CLI over the strategy / consensus / backtest / fundamentals
engine.

    python3 trader.py signals [TICKERS...]   # consensus per stock (default: watchlist)
    python3 trader.py buy                     # rank the watchlist, surface today's BUYs
    python3 trader.py portfolio               # consensus signals on your holdings.md
    python3 trader.py backtest TICKER [--years 3] [--short]
    python3 trader.py fundamentals TICKER...  # yfinance fundamental scorecard
    python3 trader.py full TICKER...          # fundamentals + technical consensus

Free data only (Yahoo Finance via yfinance). Not financial advice.
"""

from __future__ import annotations

import argparse
import sys

from common import (
    currency_symbol,
    fetch_history,
    load_holdings,
    load_watchlist,
)
from strategies import STRATEGIES, MIN_BARS, consensus, live_signals
from backtest import backtest_ticker
from walkforward import walk_forward, TRADING_DAYS, MONTH
from fundamentals import analyze_fundamentals, format_fundamentals

VOTE_EMOJI = {1: "🟢", -1: "🔴", 0: "⚪"}


def move_icon(change_pct: float) -> str:
    """Colour-coded price-direction icon (NOT a neutral arrow).

    📈 green/up · 📉 red/down · ➖ flat. Kept visually distinct from the
    consensus-verdict circles (🟢/🔴/⚪) so one line carries two clear meanings:
    the chart icon = today's move, the circle = the signal.
    """
    if change_pct > 0:
        return "📈"
    if change_pct < 0:
        return "📉"
    return "➖"


# ── Technical consensus ──────────────────────────────────────────────────────

def analyze_consensus(ticker: str, period: str = "1y") -> dict:
    df = fetch_history(ticker, period=period)
    if df.empty or len(df) < MIN_BARS:
        return {"ticker": ticker, "error": f"not enough data ({len(df)} bars, need {MIN_BARS}+)"}
    price = round(float(df["Close"].iloc[-1]), 2)
    prev = float(df["Close"].iloc[-2])
    change_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
    votes = live_signals(df)
    return {
        "ticker": ticker,
        "price": price,
        "change_pct": change_pct,
        "votes": votes,
        "consensus": consensus(votes),
        "currency": currency_symbol(ticker),
    }


def _votes_line(votes: dict[str, int]) -> str:
    return "  ".join(f"{STRATEGIES[n]['label'].split()[0]}{VOTE_EMOJI[v]}" for n, v in votes.items())


def format_consensus(r: dict) -> str:
    if "error" in r:
        return f"❌ {r['ticker']}: {r['error']}"
    c = r["consensus"]
    sym = r["currency"]
    move = move_icon(r["change_pct"])
    return (
        f"{c['emoji']} *{r['ticker']}* {sym}{r['price']}  {move} {r['change_pct']:+.2f}% "
        f"— {c['verdict']}  [net {c['net']:+d} · {c['n_buy']}🟢/{c['n_sell']}🔴/{c['n_hold']}⚪]\n"
        f"   {_votes_line(r['votes'])}"
    )


def cmd_signals(tickers: list[str]) -> int:
    tickers = tickers or load_watchlist()
    if not tickers:
        print("No tickers (watchlist.md empty?).")
        return 1
    print(f"📊 Consensus signals — {len(tickers)} stocks ({len(STRATEGIES)} strategies voting)\n")
    for t in tickers:
        print(format_consensus(analyze_consensus(t.upper())))
    return 0


def cmd_buy(_args) -> int:
    tickers = load_watchlist()
    results = [analyze_consensus(t.upper()) for t in tickers]
    ok = [r for r in results if "error" not in r]
    ok.sort(key=lambda r: r["consensus"]["net"], reverse=True)
    buys = [r for r in ok if r["consensus"]["net"] >= 2]

    print(f"🟢 *WHAT TO BUY TODAY* — ranked by signal consensus ({len(tickers)} screened)\n")
    if not buys:
        print("No stocks on a BUY consensus right now. Tape is mixed — sit on your hands.\n")
    for rank, r in enumerate(buys, 1):
        c = r["consensus"]
        print(f"{rank}. {c['emoji']} {r['ticker']} — {c['verdict']} (net {c['net']:+d}, "
              f"{c['n_buy']}/{c['n_total']} strategies bullish)  {r['currency']}{r['price']}")
    print("\n— Full ranking —")
    for r in ok:
        c = r["consensus"]
        print(f"  {c['emoji']} {r['ticker']:<7} net {c['net']:+d}  {c['verdict']}")
    print("\n_Not financial advice. Backtest signals before acting (python3 trader.py backtest TICKER)._")
    return 0


def cmd_portfolio(_args) -> int:
    tickers = load_holdings()
    if not tickers:
        print("No holdings found in holdings.md.")
        return 1
    results = [analyze_consensus(t.upper()) for t in tickers]
    ok = [r for r in results if "error" not in r]

    sells = [r for r in ok if r["consensus"]["net"] <= -2]
    adds = [r for r in ok if r["consensus"]["net"] >= 2]

    print(f"💼 *PORTFOLIO SIGNALS* — {len(tickers)} holdings, consensus of {len(STRATEGIES)} strategies\n")

    if sells:
        print("⚠️ *Holdings flashing SELL / trim:*")
        for r in sorted(sells, key=lambda r: r["consensus"]["net"]):
            c = r["consensus"]
            print(f"  {c['emoji']} {r['ticker']} — {c['verdict']} (net {c['net']:+d}, {move_icon(r['change_pct'])} {r['change_pct']:+.2f}%)")
        print()
    if adds:
        print("✅ *Holdings on a BUY consensus (add candidates):*")
        for r in sorted(adds, key=lambda r: r["consensus"]["net"], reverse=True):
            c = r["consensus"]
            print(f"  {c['emoji']} {r['ticker']} — {c['verdict']} (net {c['net']:+d})")
        print()

    print("— Full holdings consensus —")
    for r in results:
        print(format_consensus(r))
    print("\n_Going with the consensus of signals. Not financial advice._")
    return 0


# ── Backtest ─────────────────────────────────────────────────────────────────

def cmd_backtest(args) -> int:
    ticker = args.ticker.upper()
    period = f"{args.years}y"
    df = fetch_history(ticker, period=period)
    if df.empty or len(df) < MIN_BARS:
        print(f"❌ {ticker}: not enough data ({len(df)} bars).")
        return 1

    results = backtest_ticker(df, long_only=not args.short, cost_bps=args.cost)
    bh = results["BUY_HOLD"]
    mode = "long/short" if args.short else "long-only"

    start = df.index[0].date()
    end = df.index[-1].date()
    print(f"🧪 *Backtest {ticker}* — {start} → {end} ({len(df)} bars, {mode}, {args.cost:.0f}bps/trade)\n")
    header = f"{'Strategy':<22}{'Return':>9}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'Win%':>7}{'Trades':>8}{'Expo':>7}"
    print(header)
    print("-" * len(header))

    def row(name, m, label=None):
        win = "  —  " if m["win_rate"] != m["win_rate"] else f"{m['win_rate']*100:4.0f}%"
        print(f"{(label or name):<22}{m['total_return']*100:8.1f}%{m['cagr']*100:7.1f}%"
              f"{m['sharpe']:8.2f}{m['max_drawdown']*100:7.1f}%{win:>7}{m['n_trades']:8d}{m['exposure']*100:6.0f}%")

    for name, meta in STRATEGIES.items():
        row(name, results[name], meta["label"])
    print("-" * len(header))
    row("CONSENSUS", results["CONSENSUS"], "★ CONSENSUS")
    row("BUY_HOLD", bh, "Buy & Hold")

    cons = results["CONSENSUS"]
    verdict = "beat" if cons["total_return"] > bh["total_return"] else "lagged"
    print(f"\n→ Consensus {verdict} buy-and-hold "
          f"({cons['total_return']*100:+.1f}% vs {bh['total_return']*100:+.1f}%), "
          f"Sharpe {cons['sharpe']:.2f} vs {bh['sharpe']:.2f}, "
          f"max drawdown {cons['max_drawdown']*100:.1f}% vs {bh['max_drawdown']*100:.1f}%.")
    print("_Past performance is not predictive. Not financial advice._")
    return 0


# ── Walk-forward (out-of-sample) ─────────────────────────────────────────────

def cmd_walkforward(args) -> int:
    ticker = args.ticker.upper()
    df = fetch_history(ticker, period=f"{args.years}y")
    res = walk_forward(
        df,
        train_days=int(args.train * TRADING_DAYS),
        test_days=int(args.test * MONTH),
        long_only=not args.short,
        cost_bps=args.cost,
        top_k=args.top,
    )
    if "error" in res:
        print(f"❌ {ticker}: {res['error']} — try a longer --years.")
        return 1

    sel, all9, bh = res["selected_consensus"], res["all9_consensus"], res["buy_hold"]
    print(f"🔬 *Walk-forward {ticker}* — OUT-OF-SAMPLE {res['oos_start']} → {res['oos_end']} "
          f"({res['n_folds']} folds · {args.train}y train / {args.test}mo test)\n")

    print("Per fold — strategies picked in-sample, then traded out-of-sample:")
    for i, f in enumerate(res["folds"], 1):
        picks = ", ".join(STRATEGIES[s]["label"].split()[0] for s in f["selected"])
        edge = f["test_return"] - f["bh_test_return"]
        print(f"  {i}. {f['test_start']}→{f['test_end']}  "
              f"OOS {f['test_return']*100:+6.1f}% vs B&H {f['bh_test_return']*100:+6.1f}% "
              f"({edge*100:+5.1f}%)  picked[{len(f['selected'])}]: {picks}")

    header = f"\n{'Stitched OOS result':<24}{'Return':>9}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'Win%':>7}{'Trades':>8}{'Expo':>7}"
    print(header)
    print("-" * (len(header) - 1))

    def row(label, m):
        win = "  —  " if m["win_rate"] != m["win_rate"] else f"{m['win_rate']*100:4.0f}%"
        print(f"{label:<24}{m['total_return']*100:8.1f}%{m['cagr']*100:7.1f}%"
              f"{m['sharpe']:8.2f}{m['max_drawdown']*100:7.1f}%{win:>7}{m['n_trades']:8d}{m['exposure']*100:6.0f}%")

    row("★ Selected consensus", sel)
    row("All-9 consensus", all9)
    row("Buy & Hold", bh)

    gen = "held up out-of-sample" if sel["total_return"] > bh["total_return"] else "did NOT beat buy-and-hold OOS"
    vs_all = "and beat the all-9 consensus" if sel["total_return"] > all9["total_return"] else "but the all-9 consensus did as well or better"
    print(f"\n→ Strategy selection {gen} "
          f"({sel['total_return']*100:+.1f}% vs B&H {bh['total_return']*100:+.1f}%), {vs_all} "
          f"({all9['total_return']*100:+.1f}%).")
    print("_Out-of-sample ≠ future. Not financial advice._")
    return 0


# ── Fundamentals / combined ──────────────────────────────────────────────────

def cmd_fundamentals(args) -> int:
    for t in args.tickers:
        print(format_fundamentals(analyze_fundamentals(t.upper())))
        print()
    return 0


def cmd_full(args) -> int:
    for t in args.tickers:
        t = t.upper()
        fr = analyze_fundamentals(t)
        cr = analyze_consensus(t)
        print(format_fundamentals(fr))
        print()
        print("📈 *Technical consensus*")
        print(format_consensus(cr))
        if "error" not in fr and "error" not in cr:
            f_emoji = fr["grade_emoji"]
            c = cr["consensus"]
            agree = (f_emoji == "🟢" and c["net"] >= 2) or (f_emoji == "🔴" and c["net"] <= -2)
            tag = "✅ fundamentals & technicals agree" if agree else "⚖️ fundamentals & technicals diverge — read both"
            print(f"\n🧭 Combined: fundamentals {fr['grade']} ({f_emoji}) · technicals {c['verdict']} ({c['emoji']})  → {tag}")
        print("\n" + "=" * 50 + "\n")
    return 0


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Trader engine — signals, consensus, backtest, fundamentals.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("signals", help="consensus signal per stock (default: watchlist)")
    sp.add_argument("tickers", nargs="*")

    sub.add_parser("buy", help="rank watchlist and surface today's BUYs")
    sub.add_parser("portfolio", help="consensus signals on your holdings")

    bp = sub.add_parser("backtest", help="backtest strategies + consensus vs buy-and-hold")
    bp.add_argument("ticker")
    bp.add_argument("--years", type=int, default=3, help="lookback years (default 3)")
    bp.add_argument("--short", action="store_true", help="allow short positions (default long-only)")
    bp.add_argument("--cost", type=float, default=2.0, help="per-trade cost in bps (default 2)")

    wp = sub.add_parser("walkforward", help="out-of-sample walk-forward strategy selection")
    wp.add_argument("ticker")
    wp.add_argument("--years", type=int, default=6, help="total history years (default 6)")
    wp.add_argument("--train", type=float, default=2.0, help="train window in years (default 2)")
    wp.add_argument("--test", type=float, default=6.0, help="test window in months (default 6)")
    wp.add_argument("--top", type=int, default=None, help="force top-K strategies by train Sharpe")
    wp.add_argument("--short", action="store_true", help="allow short positions")
    wp.add_argument("--cost", type=float, default=2.0, help="per-trade cost in bps (default 2)")

    fp = sub.add_parser("fundamentals", help="yfinance fundamental scorecard")
    fp.add_argument("tickers", nargs="+")

    flp = sub.add_parser("full", help="fundamentals + technical consensus")
    flp.add_argument("tickers", nargs="+")

    args = p.parse_args()
    if args.cmd == "signals":
        return cmd_signals(args.tickers)
    if args.cmd == "buy":
        return cmd_buy(args)
    if args.cmd == "portfolio":
        return cmd_portfolio(args)
    if args.cmd == "backtest":
        return cmd_backtest(args)
    if args.cmd == "walkforward":
        return cmd_walkforward(args)
    if args.cmd == "fundamentals":
        return cmd_fundamentals(args)
    if args.cmd == "full":
        return cmd_full(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
