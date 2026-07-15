"""4D prediction strategies.

Each strategy reduces to a **per-position digit weight** (4 positions x 10
digits). A pick samples one digit per position independently, WITH replacement
(digits repeat in 4D), and assembles a 4-digit number. NONE beat random - the
backtest proves it. Weights are derived from the First prize history, since we
predict and score against the First prize.
"""
from __future__ import annotations

import os
from collections import Counter
from typing import Callable, Dict, List

import numpy as np
import pandas as pd

from . import fourd_config as fc
from . import fourd_ml


def _sample_number(pos_weights: List[Dict[int, float]], rng: np.random.Generator) -> str:
    digits = []
    for p in range(fc.POSITIONS):
        w = np.array([max(pos_weights[p].get(d, 0.0), 0.0) for d in fc.DIGITS], dtype=float)
        if w.sum() <= 0:
            w = np.ones(fc.N_DIGITS)
        w = w / w.sum()
        digits.append(int(rng.choice(fc.DIGITS, p=w)))
    return "".join(str(d) for d in digits)


# --- Weight functions: history -> [ {digit: weight} per position ] --------------

def uniform_weights(df: pd.DataFrame) -> List[Dict[int, float]]:
    return [{d: 1.0 for d in fc.DIGITS} for _ in range(fc.POSITIONS)]


def frequency_weights(df: pd.DataFrame) -> List[Dict[int, float]]:
    out = []
    for p in range(fc.POSITIONS):
        c = Counter(digs[p] for digs in df["first_digits"])
        out.append({d: float(c.get(d, 0) + 1) for d in fc.DIGITS})
    return out


def cold_weights(df: pd.DataFrame) -> List[Dict[int, float]]:
    out = []
    for p in range(fc.POSITIONS):
        c = Counter(digs[p] for digs in df["first_digits"])
        mx = max((c.get(d, 0) for d in fc.DIGITS), default=0)
        out.append({d: float(mx + 1 - c.get(d, 0)) for d in fc.DIGITS})
    return out


def overdue_weights(df: pd.DataFrame) -> List[Dict[int, float]]:
    n = len(df)
    out = []
    for p in range(fc.POSITIONS):
        last_seen: Dict[int, int] = {}
        for idx, digs in enumerate(df["first_digits"]):
            last_seen[digs[p]] = idx
        out.append({d: float(n - last_seen.get(d, -1)) for d in fc.DIGITS})
    return out


WEIGHT_FUNCS: Dict[str, Callable[[pd.DataFrame], List[Dict[int, float]]]] = {
    "random": uniform_weights,
    "frequency": frequency_weights,
    "cold": cold_weights,
    "overdue": overdue_weights,
}

STRATEGY_LABELS = {
    "random": "Random baseline",
    "frequency": "Hot (frequent digits)",
    "cold": "Cold (rare digits)",
    "overdue": "Due (overdue digits)",
    "ml_gbm": "ML - gradient boosting",
    "ml_logistic": "ML - logistic regression",
    "ml_mlp": "ML - neural net (MLP)",
}

STRATEGY_BLURBS = {
    "random": "A uniform random 4-digit number - the honest yardstick.",
    "frequency": "Favours the digits most often seen in each position of the First prize.",
    "cold": "Favours the digits least often seen in each position.",
    "overdue": "Favours digits that have not appeared in a position for a while.",
    "ml_gbm": "Gradient-boosted trees predicting each position's digit.",
    "ml_logistic": "A linear (logistic regression) model - the simplest ML baseline.",
    "ml_mlp": "A small neural network (multi-layer perceptron).",
}

STRATEGY_INDEX = {name: i + 1 for i, name in enumerate(STRATEGY_LABELS)}


def _make_picker(weight_fn):
    def pick(df: pd.DataFrame, rng: np.random.Generator) -> dict:
        return {"number": _sample_number(weight_fn(df), rng)}
    return pick


STRATEGIES: Dict[str, Callable[..., dict]] = {
    name: _make_picker(fn) for name, fn in WEIGHT_FUNCS.items()
}


def _make_rng(seed: int | None, strategy: str = "") -> np.random.Generator:
    base = seed if seed is not None else int.from_bytes(os.urandom(8), "little")
    return np.random.default_rng([int(base), STRATEGY_INDEX.get(strategy, 0)])


def predict(strategy: str, df: pd.DataFrame, seed: int | None = None, sets: int = 1) -> dict:
    """Generate `sets` candidate 4-digit numbers for one strategy."""
    if strategy in fourd_ml.ML_MODEL_KEYS:
        return fourd_ml.predict(strategy, df, seed=seed, sets=sets)
    if strategy not in STRATEGIES:
        raise KeyError(strategy)
    weights = WEIGHT_FUNCS[strategy](df)
    rng = _make_rng(seed, strategy)
    out = [_sample_number(weights, rng) for _ in range(max(1, sets))]
    return {"strategy": strategy, "label": STRATEGY_LABELS[strategy],
            "blurb": STRATEGY_BLURBS[strategy], "sets": out}
