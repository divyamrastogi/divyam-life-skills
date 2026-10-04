---
name: stock-alerts
description: >
  Technical stock signals, buy recommendations, portfolio signal-checks, strategy
  backtesting, and fundamental analysis. Use when the user asks which stocks to
  buy, what their portfolio is signalling, to predict/score a stock's movement,
  to backtest a strategy, or for a stock's fundamentals (e.g. "what should I buy",
  "any signals in my portfolio", "backtest AMD", "is GOOG a buy", "run the
  signals"). Free data only (Yahoo Finance via yfinance).
---

# Stock Alerts & Trader Engine

A consensus-of-strategies engine: nine well-known trading strategies each cast a
vote (BUY / HOLD / SELL) on every stock, and we **go with the consensus**. Every
strategy is independently **backtestable** so you can see which signals actually
work before trusting them. Adds programmatic **fundamental analysis** that
combines with the technical read.

Reads tickers from the central `~/clawd/memory/watchlist.md` (watchlist)
and `~/clawd/trader-analyst/holdings.md` (what you own) — single sources of truth.

## Primary CLI — `trader.py`

```bash
cd ~/clawd/skills/stock-alerts

python3 trader.py signals [TICKERS...]   # consensus signal per stock (default: whole watchlist)
python3 trader.py buy                     # rank the watchlist, surface today's BUYs
python3 trader.py portfolio               # consensus signals on your holdings.md
python3 trader.py backtest TICKER [--years 3] [--short] [--cost 2]
python3 trader.py walkforward TICKER [--years 6] [--train 2] [--test 6] [--top K]
python3 trader.py fundamentals TICKER...  # yfinance fundamental scorecard
python3 trader.py full TICKER...          # fundamentals + technical consensus, combined verdict
```

### What each answers (maps to the asks)
- **Predict movement / known algorithms** → `signals` (nine textbook strategies vote)
- **Which stocks to buy** → `buy` (ranks the watchlist by consensus, lists the BUYs)
- **Eval / does it work** → `backtest` (per-strategy + consensus vs buy-and-hold)
- **Portfolio signals, by consensus** → `portfolio` (BUY/SELL consensus on holdings)
- **Fundamental analysis** → `fundamentals` and `full`

## The nine strategies (consensus voters)

| Strategy | Kind | Signal |
|----------|------|--------|
| SMA 50/200 Trend | trend | golden/death cross |
| MACD Momentum | trend | MACD vs signal line |
| Donchian Breakout | trend | 20-day channel breakout (turtle) |
| ADX Directional | trend | +DI/−DI when ADX>25 |
| 6-Month Momentum | trend | 126-day rate of change |
| OBV Volume Trend | trend | OBV vs 20-day average |
| RSI Mean-Reversion | mean-rev | oversold/overbought |
| Bollinger Mean-Reversion | mean-rev | close outside the bands |
| Stochastic | mean-rev | %K/%D out of extremes |

**Consensus = sum of votes (net).** Verdict: net ≥ +5 🟢🟢 STRONG BUY · ≥ +2 🟢 BUY ·
−1…+1 ⚪ NEUTRAL · ≤ −2 🔴 SELL · ≤ −5 🔴🔴 STRONG SELL.

## Backtesting (the eval)

Replays each strategy's vote series over Yahoo Finance history with **no
lookahead** (acts on the prior bar's vote) and a small per-trade cost. Reports
total return, CAGR, Sharpe, max drawdown, trade win-rate, # trades and market
exposure for every strategy **and** the consensus, next to a buy-and-hold
baseline. Long-only by default; `--short` enables shorts.

```bash
python3 trader.py backtest AMD --years 5
```

Use this to decide which signals to weight — a strategy that loses to buy-and-hold
on a name is noise for that name.

### Walk-forward (out-of-sample)

`backtest` is in-sample. `walkforward` is the honest test: on each rolling TRAIN
window it selects the strategies that actually worked (positive Sharpe), then
trades **only that selection** on the next unseen TEST window — selection uses
train data only, performance is measured on test data only. It stitches every
test window into one out-of-sample curve and compares it to (a) the "always all
9" consensus and (b) buy-and-hold.

```bash
python3 trader.py walkforward AMD --years 6          # 2y train / 6mo test, rolling
python3 trader.py walkforward GOOG --years 6 --top 5 # force top-5 strategies by train Sharpe
```

Read the per-fold line to see which strategies got picked each period and
whether the pick generalised. If selected-consensus can't beat the simple all-9
consensus out-of-sample, the selection is overfitting — trust the plain
consensus instead.

## Fundamentals

`fundamentals` pulls valuation (P/E, P/B, PEG), profitability (margins, ROE),
balance sheet (debt/equity, current ratio) and growth (revenue, FCF) from
yfinance and grades each 🟢/🟡/🔴 into a single grade. `full` shows fundamentals
+ technical consensus and flags whether they agree or diverge. For a deeper
qualitative dive (Reddit sentiment, earnings-quality red flags) use the separate
`stock-analyst` skill.

## Module layout

- `trader.py` — unified CLI (above)
- `strategies.py` — the nine vote-producing strategies + consensus logic
- `backtest.py` — the in-sample backtest harness
- `walkforward.py` — out-of-sample walk-forward strategy selection
- `fundamentals.py` — yfinance fundamental scorecard
- `common.py` — watchlist/holdings parsing + cached data fetch
- `alert_engine.py` — original 10-indicator scorer (kept for the existing cron job)

## Cron / WhatsApp

The existing cron job still runs `alert_engine.py` and sends to the "Trader Bot"
WhatsApp group (`120363411953543280@g.us`). To switch the cron to the consensus
engine, point it at `python3 trader.py signals` (or `buy` / `portfolio`). The
output is already WhatsApp-friendly markdown.

## Notes
- All output ends with a not-financial-advice disclaimer.
- LSE tickers in holdings.md (e.g. `QDE`, `VUSA`) get a `.L` suffix automatically.
- Requires `yfinance`, `pandas`, `numpy` (already installed).
