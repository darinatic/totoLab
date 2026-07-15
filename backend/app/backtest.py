"""Walk-forward backtest - the honest centrepiece.

For each draw in the test window we predict using ONLY the draws before it, then
score the prediction against what was actually drawn. We report the average
number of matched main numbers per strategy, with bootstrap confidence
intervals, alongside the random baseline and the theoretical expectation
(6 * 6/49 = 0.735). If a strategy had real predictive power its interval would
sit clearly above random's. It never does.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from . import config, ml, strategies
from .ml import MLPredictor

ALPHA = 0.05


def _matches(predicted: List[int], actual: List[int]) -> int:
    return len(set(predicted) & set(actual))


def _bootstrap_ci(values: np.ndarray, rng: np.random.Generator,
                  n_boot: int = 1000, alpha: float = 0.05) -> tuple[float, float]:
    if len(values) == 0:
        return (float("nan"), float("nan"))
    means = np.array([
        rng.choice(values, size=len(values), replace=True).mean()
        for _ in range(n_boot)
    ])
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def run(df: pd.DataFrame, test_size: int = 150, seed: int = 0,
        ml_refit_every: int = 25, include_ml: bool = True) -> dict:
    """Walk-forward evaluation over the last `test_size` draws.

    Returns per-strategy mean matches, bootstrap CI, prize-tier hit rates, and
    the theoretical random expectation for reference.
    """
    n = len(df)
    start = max(config.PICK * 10, n - test_size)  # keep a warm-up history
    test_idx = list(range(start, n))
    rng = np.random.default_rng(seed)

    strat_names = list(strategies.STRATEGIES.keys())
    ml_keys = ml.ML_MODEL_KEYS if include_ml else []
    match_series: Dict[str, List[int]] = {s: [] for s in strat_names}
    for k in ml_keys:
        match_series[k] = []

    # One re-fittable model per ML family (refit periodically to bound cost).
    ml_models: Dict[str, Optional[MLPredictor]] = {k: None for k in ml_keys}

    for step, t in enumerate(test_idx):
        history = df.iloc[:t]
        actual = df.iloc[t]["numbers"]

        for s in strat_names:
            # Independent stream per (strategy, draw): reproducible, varied across
            # draws, and NOT shared between strategies.
            step_rng = np.random.default_rng([seed, t, strategies.STRATEGY_INDEX[s]])
            pred = strategies.STRATEGIES[s](history, step_rng)
            match_series[s].append(_matches(pred["numbers"], actual))

        for k in ml_keys:
            if ml_models[k] is None or step % ml_refit_every == 0:
                ml_models[k] = MLPredictor(k).fit(history)
            pred = ml_models[k].predict_next(history, seed=seed + t)
            match_series[k].append(_matches(pred["numbers"], actual))

    baseline = config.EXPECTED_RANDOM_MATCHES  # exact, noise-free random expectation
    # Bonferroni-correct the significance threshold: we test several strategies,
    # so ~1-in-20 would look "significant" by chance without correction.
    n_tested = sum(1 for s in match_series if s != "random")
    sig_threshold = ALPHA / max(n_tested, 1)

    results = []
    for s, series in match_series.items():
        arr = np.array(series, dtype=float)
        lo, hi = _bootstrap_ci(arr, rng)
        # one-sided test H0: mean == baseline vs H1: mean > baseline
        if s == "random" or len(arr) < 3:
            p_one_sided = None
        elif arr.std(ddof=1) == 0:
            # Zero variance: a constant score is decisive - significant iff it
            # sits strictly above the baseline (e.g. a perfect predictor).
            p_one_sided = 0.0 if arr.mean() > baseline else 1.0
        else:
            t, p_two = stats.ttest_1samp(arr, baseline)
            p_one_sided = (p_two / 2) if t > 0 else (1 - p_two / 2)
        beats = bool(
            s != "random"
            and arr.mean() > baseline
            and p_one_sided is not None
            and p_one_sided < sig_threshold
        )
        results.append({
            "strategy": s,
            "label": strategies.STRATEGY_LABELS[s],
            "mean_matches": round(float(arr.mean()), 4),
            "ci_low": round(lo, 4),
            "ci_high": round(hi, 4),
            "hit_rate_3plus": round(float((arr >= 3).mean()), 4),
            "best_match": int(arr.max()),
            "n_tests": len(series),
            "p_vs_random": round(p_one_sided, 4) if p_one_sided is not None else None,
            "beats_random": beats,
        })
    results.sort(key=lambda r: r["mean_matches"], reverse=True)
    any_beats = any(r["beats_random"] for r in results)

    return {
        "test_size": len(test_idx),
        "theoretical_random": round(baseline, 4),
        "sig_threshold": round(sig_threshold, 4),
        "results": results,
        "any_beats_random": any_beats,
        "verdict": (
            "No strategy beats the random baseline at a statistically significant "
            "level. Consistent with an unpredictable, fair lottery - exactly as "
            "expected."
            if not any_beats else
            "A strategy edged past the baseline in this sample. With several "
            "strategies tested on finite data, occasional false positives are "
            "expected and do not replicate out of sample - they are noise, not an edge."
        ),
        "disclaimer": config.DISCLAIMER,
    }
