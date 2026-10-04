#!/usr/bin/env python3
"""Walk-forward (out-of-sample) evaluation.

The strategies are fixed-rule, so the thing worth validating out-of-sample is
the *consensus composition*: does "use the strategies that have been working"
actually generalise, or is it curve-fitting?

Procedure (rolling, non-overlapping test windows):

    |————— train —————|—— test ——|
              step ──▶ |————— train —————|—— test ——|

  1. On each TRAIN window, backtest all 9 strategies and SELECT the ones that
     worked (positive Sharpe; fall back to the top few if none clear the bar).
  2. On the next, unseen TEST window, build the consensus from ONLY the
     selected strategies and record its returns.
  3. Stitch every test window into one out-of-sample equity curve.

Selection uses train data only; performance is measured on test data only — so
there's no lookahead. We report the selected-consensus OOS result next to two
honest baselines: the "always all 9" consensus over the same OOS span, and
buy-and-hold.

Votes are computed once on the full history (indicators stay properly warmed
up) and then sliced per window — slicing a backward-looking vote series can't
leak the future.
"""

from __future__ import annotations

import pandas as pd

from strategies import STRATEGIES, compute_votes
from backtest import simulate, metrics_from_returns, consensus_votes, buy_and_hold

TRADING_DAYS = 252
MONTH = 21


def _select_strategies(train_metrics: dict[str, dict], top_k: int | None) -> list[str]:
    """Pick strategies from train-window metrics.

    Default: every strategy with a positive in-sample Sharpe. If fewer than 3
    clear that bar, take the top 3 by Sharpe so the consensus is never built
    from a single lucky signal. ``top_k`` forces exactly the top-k by Sharpe.
    """
    ranked = sorted(STRATEGIES, key=lambda n: train_metrics[n]["sharpe"], reverse=True)
    if top_k:
        return ranked[:top_k]
    positive = [n for n in ranked if train_metrics[n]["sharpe"] > 0]
    return positive if len(positive) >= 3 else ranked[:3]


def walk_forward(
    df: pd.DataFrame,
    train_days: int = 2 * TRADING_DAYS,
    test_days: int = 6 * MONTH,
    long_only: bool = True,
    cost_bps: float = 2.0,
    top_k: int | None = None,
) -> dict:
    """Run rolling walk-forward selection over *df*."""
    votes = compute_votes(df)
    daily_ret = df["Close"].pct_change().fillna(0)
    n = len(df)

    if n < train_days + test_days:
        return {"error": f"need {train_days + test_days} bars, have {n}"}

    folds = []
    sel_ret_parts, sel_pos_parts = [], []   # stitched selected-consensus OOS
    all_ret_parts, all_pos_parts = [], []   # stitched all-9-consensus OOS

    start = 0
    while start + train_days + test_days <= n:
        tr = slice(start, start + train_days)
        te = slice(start + train_days, start + train_days + test_days)

        # 1. Select on train window.
        train_metrics = {}
        for name in STRATEGIES:
            pos, ret = simulate(daily_ret.iloc[tr], votes[name].iloc[tr], long_only, cost_bps)
            train_metrics[name] = metrics_from_returns(ret, pos)
        selected = _select_strategies(train_metrics, top_k)

        # 2. Test window — selected consensus.
        sel_votes = consensus_votes({name: votes[name].iloc[te] for name in selected})
        sel_pos, sel_ret = simulate(daily_ret.iloc[te], sel_votes, long_only, cost_bps)
        # ...and the all-9 baseline on the same test window.
        all_votes = consensus_votes({name: votes[name].iloc[te] for name in STRATEGIES})
        all_pos, all_ret = simulate(daily_ret.iloc[te], all_votes, long_only, cost_bps)

        sel_ret_parts.append(sel_ret); sel_pos_parts.append(sel_pos)
        all_ret_parts.append(all_ret); all_pos_parts.append(all_pos)

        folds.append({
            "train_start": df.index[tr.start].date(),
            "test_start": df.index[te.start].date(),
            "test_end": df.index[min(te.stop, n) - 1].date(),
            "selected": selected,
            "test_return": float((1 + sel_ret).prod() - 1),
            "bh_test_return": float((1 + daily_ret.iloc[te]).prod() - 1),
        })
        start += test_days

    # 3. Stitch OOS curves.
    sel_ret = pd.concat(sel_ret_parts); sel_pos = pd.concat(sel_pos_parts)
    all_ret = pd.concat(all_ret_parts); all_pos = pd.concat(all_pos_parts)
    oos = df.loc[sel_ret.index]

    return {
        "n_folds": len(folds),
        "oos_start": sel_ret.index[0].date(),
        "oos_end": sel_ret.index[-1].date(),
        "folds": folds,
        "selected_consensus": metrics_from_returns(sel_ret, sel_pos),
        "all9_consensus": metrics_from_returns(all_ret, all_pos),
        "buy_hold": buy_and_hold(oos),
    }
