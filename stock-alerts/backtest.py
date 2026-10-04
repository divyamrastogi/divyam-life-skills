#!/usr/bin/env python3
"""Backtesting harness — the eval for our signals.

Replays each strategy's vote series over historical Yahoo Finance data (free)
and reports how it would actually have performed versus buying and holding.

No lookahead: the position held on day *t* is decided by the vote from day
*t-1* (``votes.shift(1)``). A small per-trade cost is applied on entries/exits
so results aren't fantasy-frictionless.

Metrics per strategy and for the consensus:
  total return · CAGR · Sharpe · max drawdown · trade win-rate · # trades
all next to the buy-and-hold baseline for the same window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies import STRATEGIES, compute_votes

TRADING_DAYS = 252


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1).min())


def _trade_stats(position: pd.Series, strat_ret: pd.Series):
    """Win-rate and trade count from runs of constant non-zero position."""
    group = (position != position.shift()).cumsum()
    wins = trades = 0
    for _, idx in position.groupby(group).groups.items():
        seg_pos = position.loc[idx]
        if seg_pos.iloc[0] == 0:
            continue
        trades += 1
        seg_ret = (1 + strat_ret.loc[idx]).prod() - 1
        if seg_ret > 0:
            wins += 1
    win_rate = (wins / trades) if trades else 0.0
    return win_rate, trades


def simulate(daily_ret: pd.Series, votes: pd.Series, long_only: bool = True, cost_bps: float = 2.0):
    """Turn a vote series into (position, net-of-cost return) series.

    Position on day *t* is set by the vote from *t-1* (``shift(1)``) — no
    lookahead. A per-trade cost is charged whenever the position changes.
    """
    pos = votes.shift(1).fillna(0)
    if long_only:
        pos = (pos > 0).astype(int)
    else:
        pos = np.sign(pos).astype(int)
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * (cost_bps / 10_000.0)
    strat_ret = pos * daily_ret - cost
    return pos, strat_ret


def metrics_from_returns(strat_ret: pd.Series, pos: pd.Series) -> dict:
    """Performance metrics from a (position, return) pair."""
    equity = (1 + strat_ret).cumprod()
    years = max(len(strat_ret) / TRADING_DAYS, 1e-9)
    std = strat_ret.std()
    win_rate, n_trades = _trade_stats(pos, strat_ret)
    return {
        "total_return": float(equity.iloc[-1] - 1) if len(equity) else 0.0,
        "cagr": float(equity.iloc[-1] ** (1 / years) - 1) if len(equity) else 0.0,
        "sharpe": float(strat_ret.mean() / std * np.sqrt(TRADING_DAYS)) if std else 0.0,
        "vol": float(std * np.sqrt(TRADING_DAYS)),
        "max_drawdown": _max_drawdown(equity) if len(equity) else 0.0,
        "win_rate": win_rate,
        "n_trades": n_trades,
        "exposure": float((pos != 0).mean()) if len(pos) else 0.0,
    }


def backtest_signal(
    df: pd.DataFrame,
    votes: pd.Series,
    long_only: bool = True,
    cost_bps: float = 2.0,
) -> dict:
    """Backtest one vote series against *df*'s closes."""
    daily_ret = df["Close"].pct_change().fillna(0)
    pos, strat_ret = simulate(daily_ret, votes, long_only, cost_bps)
    return metrics_from_returns(strat_ret, pos)


def buy_and_hold(df: pd.DataFrame) -> dict:
    daily_ret = df["Close"].pct_change().fillna(0)
    equity = (1 + daily_ret).cumprod()
    years = max(len(df) / TRADING_DAYS, 1e-9)
    return {
        "total_return": float(equity.iloc[-1] - 1),
        "cagr": float(equity.iloc[-1] ** (1 / years) - 1),
        "sharpe": float(daily_ret.mean() / daily_ret.std() * np.sqrt(TRADING_DAYS)) if daily_ret.std() else 0.0,
        "vol": float(daily_ret.std() * np.sqrt(TRADING_DAYS)),
        "max_drawdown": _max_drawdown(equity),
        "win_rate": float("nan"),
        "n_trades": 1,
        "exposure": 1.0,
    }


def consensus_votes(votes_by_strategy: dict[str, pd.Series], buy_threshold: int = 2) -> pd.Series:
    """Daily consensus position from the sum of all strategy votes.

    Mirrors the live verdict: net >= +threshold → long, net <= -threshold →
    short (only used when shorts are enabled), otherwise flat.
    """
    net = sum(votes_by_strategy.values())
    vote = pd.Series(0, index=net.index)
    vote[net >= buy_threshold] = 1
    vote[net <= -buy_threshold] = -1
    return vote


def backtest_ticker(df: pd.DataFrame, long_only: bool = True, cost_bps: float = 2.0) -> dict:
    """Backtest every strategy + the consensus + buy-and-hold on one ticker."""
    votes = compute_votes(df)
    results: dict[str, dict] = {}
    for name in STRATEGIES:
        results[name] = backtest_signal(df, votes[name], long_only, cost_bps)
    results["CONSENSUS"] = backtest_signal(df, consensus_votes(votes), long_only, cost_bps)
    results["BUY_HOLD"] = buy_and_hold(df)
    return results
