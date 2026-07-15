"""Prediction strategies.

Each strategy reduces to a **weight per number**, computed from the history
available so far. A pick is then `count` distinct numbers sampled without
replacement in proportion to those weights. NONE of these beat random - the
backtest proves it. They exist to demonstrate the ideas and be measured honestly.

Randomness flows through an injected numpy Generator, and each strategy uses an
independent stream (see `_make_rng`) so similar weightings never collapse to the
same picks.
"""
from __future__ import annotations

import os
from collections import Counter
from itertools import combinations
from typing import Callable, Dict, List

import numpy as np
import pandas as pd

from . import config


def _weighted_sample(
    weights: Dict[int, float], rng: np.random.Generator, count: int = config.PICK
) -> List[int]:
    """Sample `count` distinct numbers without replacement, proportional to weights."""
    count = max(1, min(count, config.POOL_SIZE))
    nums = np.array(config.POOL)
    w = np.array([max(weights.get(n, 0.0), 0.0) for n in config.POOL], dtype=float)
    if w.sum() <= 0:
        w = np.ones_like(w)
    w = w / w.sum()
    chosen = rng.choice(nums, size=count, replace=False, p=w)
    return sorted(int(x) for x in chosen)


# --- Weight functions: history -> {number: weight} ------------------------------

def uniform_weights(df: pd.DataFrame) -> Dict[int, float]:
    """The honesty yardstick: every number equally likely."""
    return {n: 1.0 for n in config.POOL}


def frequency_weights(df: pd.DataFrame) -> Dict[int, float]:
    """'Hot': weight by appearance frequency (+1 smoothing)."""
    counts = Counter(n for row in df["numbers"] for n in row)
    return {n: float(counts.get(n, 0) + 1) for n in config.POOL}


def cold_weights(df: pd.DataFrame) -> Dict[int, float]:
    """'Cold': the mirror of hot - least-drawn numbers get the most weight."""
    counts = Counter(n for row in df["numbers"] for n in row)
    max_c = max((counts.get(n, 0) for n in config.POOL), default=0)
    return {n: float(max_c + 1 - counts.get(n, 0)) for n in config.POOL}


def overdue_weights(df: pd.DataFrame) -> Dict[int, float]:
    """'Due': weight by how long since each number last appeared."""
    n_draws = len(df)
    last_seen: Dict[int, int] = {}
    for idx, row in enumerate(df["numbers"]):
        for num in row:
            last_seen[num] = idx
    return {n: float(n_draws - last_seen.get(n, -1)) for n in config.POOL}


def markov_scores(df: pd.DataFrame) -> Dict[int, float]:
    """Conditional co-occurrence vs the most recent draw.

    Raw co-occurrence counts are dominated by base rate (a frequent number
    co-occurs with everything), making them a near-copy of the frequency
    strategy. We use the *conditional rate* - of the times a number appeared, how
    often was it alongside the last draw's numbers - dividing out each number's
    own frequency to isolate genuine association. A small floor keeps every
    number sampleable.
    """
    counts = Counter(n for row in df["numbers"] for n in row)
    co = np.zeros((config.POOL_SIZE + 1, config.POOL_SIZE + 1))
    for row in df["numbers"]:
        for a, b in combinations(row, 2):
            co[a][b] += 1
            co[b][a] += 1
    last = df["numbers"].iloc[-1] if len(df) else []
    rate = {
        n: float(sum(co[n][m] for m in last)) / (counts.get(n, 0) + 1)
        for n in config.POOL
    }
    floor = 0.1 * (sum(rate.values()) / len(rate) or 1.0)
    return {n: rate[n] + floor for n in config.POOL}


def contrarian_weights(df: pd.DataFrame) -> Dict[int, float]:
    """'Contrarian': favour numbers above 31.

    This is the ONE strategy with a real rationale - not better odds of winning,
    but numbers most players avoid (birthdays/dates are 1-31) mean a jackpot is
    shared with fewer people IF you win. Purely a payout-sharing argument.
    """
    return {n: (3.0 if n > 31 else 1.0) for n in config.POOL}


WEIGHT_FUNCS: Dict[str, Callable[[pd.DataFrame], Dict[int, float]]] = {
    "random": uniform_weights,
    "frequency": frequency_weights,
    "cold": cold_weights,
    "overdue": overdue_weights,
    "markov": markov_scores,
    "contrarian": contrarian_weights,
}

STRATEGY_LABELS = {
    "random": "Random baseline",
    "frequency": "Hot (frequency-weighted)",
    "cold": "Cold (rarely drawn)",
    "overdue": "Due (gap-weighted)",
    "markov": "Co-occurrence (Markov)",
    "contrarian": "Contrarian (unpopular numbers)",
    "ml_gbm": "ML - gradient boosting",
    "ml_logistic": "ML - logistic regression",
    "ml_mlp": "ML - neural net (MLP)",
}

STRATEGY_BLURBS = {
    "random": "A uniform random ticket - the honest yardstick every method is measured against.",
    "frequency": "Weighted toward 'hot' numbers that have appeared most often.",
    "cold": "Weighted toward 'cold' numbers that have appeared least often.",
    "overdue": "Weighted toward 'due' numbers that have not appeared in a while.",
    "markov": "Favours numbers that historically co-occur with the last draw.",
    "contrarian": "Favours numbers above 31 that players avoid - smaller jackpot split if you win.",
    "ml_gbm": "Gradient-boosted trees predicting each number's chance of appearing next.",
    "ml_logistic": "A linear (logistic regression) model - the simplest ML baseline.",
    "ml_mlp": "A small neural network (multi-layer perceptron).",
}

# Stable per-strategy offset so each strategy draws from an INDEPENDENT random
# stream even when callers pass the same top-level seed.
STRATEGY_INDEX = {name: i + 1 for i, name in enumerate(STRATEGY_LABELS)}


def _make_picker(weight_fn):
    def pick(df: pd.DataFrame, rng: np.random.Generator, count: int = config.PICK) -> dict:
        weights = weight_fn(df)
        return {"numbers": _weighted_sample(weights, rng, count)}
    return pick


# Backtest-compatible single-set pickers: (df, rng) -> {"numbers": [...]}
STRATEGIES: Dict[str, Callable[..., dict]] = {
    name: _make_picker(fn) for name, fn in WEIGHT_FUNCS.items()
}


def _make_rng(seed: int | None, strategy: str = "") -> np.random.Generator:
    """Reproducible-but-strategy-distinct RNG. Random base when seed is None."""
    base = seed if seed is not None else int.from_bytes(os.urandom(8), "little")
    return np.random.default_rng([int(base), STRATEGY_INDEX.get(strategy, 0)])


def predict(
    strategy: str,
    df: pd.DataFrame,
    seed: int | None = None,
    count: int = config.PICK,
    sets: int = 1,
) -> dict:
    """Generate `sets` independent picks of `count` numbers for one strategy."""
    if strategy not in STRATEGIES:
        raise KeyError(strategy)
    rng = _make_rng(seed, strategy)
    weights = WEIGHT_FUNCS[strategy](df)
    out = [_weighted_sample(weights, rng, count) for _ in range(max(1, sets))]
    return {
        "strategy": strategy,
        "label": STRATEGY_LABELS[strategy],
        "blurb": STRATEGY_BLURBS[strategy],
        "sets": out,
    }
