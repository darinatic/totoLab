"""Machine-learning 'prediction' for 4D - honest framing.

We reframe as per-(position, digit) binary questions: "will digit d land in
position p of the next First prize?" Features come from the history *before* the
draw. We pick the highest-probability digit per position and assemble a 4-digit
number. Reuses the same three model families as Toto (gradient boosting, logistic
regression, MLP). Confirmed by the backtest: none beats random.

Training history is capped (recent draws only) to keep the walk-forward backtest
affordable - older draws carry no signal anyway.
"""
from __future__ import annotations

import warnings
from typing import List

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning

from . import fourd_config as fc
from .ml import ML_BUILDERS, ML_MODEL_KEYS  # reuse the 3-family registry

WINDOWS = (10, 25, 50)
MAX_TRAIN = 600  # cap training history for speed


def _features(hist: List[List[int]], position: int, digit: int) -> List[float]:
    n = len(hist)
    feats: List[float] = []
    for w in WINDOWS:
        window = hist[-w:]
        cnt = sum(1 for digs in window if digs[position] == digit)
        feats.append(cnt / max(len(window), 1))
    gap = n
    for i in range(n - 1, -1, -1):
        if hist[i][position] == digit:
            gap = n - 1 - i
            break
    feats.append(gap / 50.0)
    total = sum(1 for digs in hist if digs[position] == digit)
    feats.append(total / max(n, 1))
    feats.append(position / fc.POSITIONS)
    feats.append(digit / fc.N_DIGITS)
    return feats


def build_dataset(df: pd.DataFrame, min_history: int = 50, max_train: int = MAX_TRAIN):
    seq = list(df["first_digits"])
    X: List[List[float]] = []
    y: List[int] = []
    for t in range(min_history, len(seq)):
        hist = seq[max(0, t - max_train):t]
        target = seq[t]
        for p in range(fc.POSITIONS):
            for d in fc.DIGITS:
                X.append(_features(hist, p, d))
                y.append(1 if target[p] == d else 0)
    return np.array(X), np.array(y)


class FourDMLPredictor:
    def __init__(self, model_key: str = "ml_gbm") -> None:
        self.model_key = model_key
        self.model = None

    def fit(self, df: pd.DataFrame, min_history: int = 50) -> "FourDMLPredictor":
        X, y = build_dataset(df, min_history)
        if len(X) == 0 or len(set(y)) < 2:
            self.model = None
            return self
        self.model = ML_BUILDERS[self.model_key]()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            self.model.fit(X, y)
        return self

    def position_probs(self, df: pd.DataFrame) -> np.ndarray:
        """Return a 4x10 array of P(digit d at position p) for the next draw."""
        if self.model is None:
            return np.full((fc.POSITIONS, fc.N_DIGITS), 1.0 / fc.N_DIGITS)
        hist = list(df["first_digits"])[-MAX_TRAIN:]
        probs = np.zeros((fc.POSITIONS, fc.N_DIGITS))
        for p in range(fc.POSITIONS):
            feats = np.array([_features(hist, p, d) for d in fc.DIGITS])
            probs[p] = self.model.predict_proba(feats)[:, 1]
        return probs

    def predict_next(self, df: pd.DataFrame, seed: int | None = None) -> dict:
        probs = self.position_probs(df)
        number = "".join(str(int(probs[p].argmax())) for p in range(fc.POSITIONS))
        return {"number": number}


def predict(model_key: str, df: pd.DataFrame, seed: int | None = None, sets: int = 1) -> dict:
    from . import fourd_strategies  # local import avoids a cycle
    probs = FourDMLPredictor(model_key).fit(df).position_probs(df)
    top = "".join(str(int(probs[p].argmax())) for p in range(fc.POSITIONS))
    out = [top]
    rng = fourd_strategies._make_rng(seed, model_key)
    for _ in range(max(1, sets) - 1):
        digits = []
        for p in range(fc.POSITIONS):
            w = probs[p] / probs[p].sum() if probs[p].sum() > 0 else None
            digits.append(int(rng.choice(fc.DIGITS, p=w)))
        out.append("".join(str(d) for d in digits))
    return {"strategy": model_key, "label": fourd_strategies.STRATEGY_LABELS[model_key],
            "blurb": fourd_strategies.STRATEGY_BLURBS[model_key], "sets": out}
