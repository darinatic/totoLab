"""Machine-learning 'prediction' - honest framing.

We reframe the impossible task (predict 6 of 49) as 49 per-number binary
questions: "will number k appear in the next draw?" For each (draw, number) we
build features from the history *before* that draw and train a classifier. We
then pick the 6 numbers with the highest predicted probability.

Three model families are offered - gradient boosting, logistic regression, and a
small neural network - so the backtest can show that linear, tree-ensemble, AND
neural models all fail to beat random. The value is demonstrating the techniques
and measuring them honestly, not a real edge.
"""
from __future__ import annotations

import warnings
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier

from . import config

# recent-window sizes used for frequency features
WINDOWS = (10, 25, 50)


def _build_gbm():
    return GradientBoostingClassifier(
        n_estimators=60, max_depth=3, learning_rate=0.1, random_state=0
    )


def _build_logistic():
    return LogisticRegression(max_iter=1000, random_state=0)


def _build_mlp():
    return MLPClassifier(hidden_layer_sizes=(16,), max_iter=200, random_state=0)


# The ML model registry. Each key is also a strategy key in strategies.STRATEGY_LABELS.
ML_BUILDERS = {
    "ml_gbm": _build_gbm,
    "ml_logistic": _build_logistic,
    "ml_mlp": _build_mlp,
}
ML_MODEL_KEYS = list(ML_BUILDERS)


def _features_for_draw(history_numbers: List[List[int]], number: int) -> List[float]:
    """Features for one number given all draws strictly before the target draw."""
    n_hist = len(history_numbers)
    feats: List[float] = []
    # recent-frequency features over several windows
    for w in WINDOWS:
        window = history_numbers[-w:]
        cnt = sum(1 for row in window for n in row if n == number)
        feats.append(cnt / max(len(window), 1))
    # gap: draws since last seen (normalised)
    gap = n_hist
    for i in range(n_hist - 1, -1, -1):
        if number in history_numbers[i]:
            gap = n_hist - 1 - i
            break
    feats.append(gap / 50.0)
    # overall frequency
    total = sum(1 for row in history_numbers for n in row if n == number)
    feats.append(total / max(n_hist, 1))
    # the number itself (lets the model express any positional bias - there is none)
    feats.append(number / config.POOL_SIZE)
    return feats


def build_dataset(df: pd.DataFrame, min_history: int = 50):
    """Build (X, y) over all draws that have at least `min_history` prior draws."""
    numbers_seq = list(df["numbers"])
    X: List[List[float]] = []
    y: List[int] = []
    for t in range(min_history, len(numbers_seq)):
        history = numbers_seq[:t]
        target = set(numbers_seq[t])
        for num in config.POOL:
            X.append(_features_for_draw(history, num))
            y.append(1 if num in target else 0)
    return np.array(X), np.array(y)


class MLPredictor:
    """Thin wrapper around one of the registered classifiers."""

    def __init__(self, model_key: str = "ml_gbm") -> None:
        self.model_key = model_key
        self.model = None

    def fit(self, df: pd.DataFrame, min_history: int = 50) -> "MLPredictor":
        X, y = build_dataset(df, min_history)
        if len(X) == 0 or len(set(y)) < 2:
            self.model = None
            return self
        self.model = ML_BUILDERS[self.model_key]()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            self.model.fit(X, y)
        return self

    def proba(self, df: pd.DataFrame) -> dict:
        """P(each number appears in the next draw). Uniform if the model is unfit."""
        if self.model is None:
            return {n: 1.0 for n in config.POOL}
        history = list(df["numbers"])
        feats = np.array([_features_for_draw(history, n) for n in config.POOL])
        p = self.model.predict_proba(feats)[:, 1]
        return {n: float(v) for n, v in zip(config.POOL, p)}

    def predict_next(self, df: pd.DataFrame, seed: int | None = None) -> dict:
        """Backtest-compatible single pick: the 6 numbers with highest P(next)."""
        scores = self.proba(df)
        nums = sorted(sorted(config.POOL, key=lambda n: scores[n], reverse=True)[:config.PICK])
        return {"numbers": nums}


def predict(model_key: str, df: pd.DataFrame, seed: int | None = None,
            count: int = config.PICK, sets: int = 1) -> dict:
    """Train `model_key` on the whole history, then produce `sets` picks.

    Set 1 is the model's actual top-`count` by probability; any further sets are
    sampled in proportion to those probabilities for variety.
    """
    from . import strategies  # local import avoids a cycle
    scores = MLPredictor(model_key).fit(df).proba(df)
    top = sorted(sorted(config.POOL, key=lambda n: scores[n], reverse=True)[:count])
    out = [top]
    rng = strategies._make_rng(seed, model_key)
    for _ in range(max(1, sets) - 1):
        out.append(strategies._weighted_sample(scores, rng, count))
    return {"strategy": model_key, "label": strategies.STRATEGY_LABELS[model_key],
            "blurb": strategies.STRATEGY_BLURBS[model_key], "sets": out}
