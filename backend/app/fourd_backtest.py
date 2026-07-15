"""Walk-forward backtest for 4D - the honest centrepiece.

For each draw we predict using ONLY prior draws, then score the predicted 4-digit
number against the actual First prize by **matched digit-positions** (0-4). A
random guess matches 4 * 1/10 = 0.4 positions on average. We also report the
exact-hit rate against any of the 23 winning numbers (random = 23/10000). If a
strategy had real skill its interval would clear 0.4. It never does.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from . import fourd_config as fc
from . import fourd_ml, fourd_strategies
from .fourd_ml import FourDMLPredictor

ALPHA = 0.05


def _digit_matches(predicted: str, actual_first: str) -> int:
    return sum(1 for a, b in zip(predicted, actual_first) if a == b)


def _bootstrap_ci(values: np.ndarray, rng: np.random.Generator,
                  n_boot: int = 1000, alpha: float = 0.05) -> tuple[float, float]:
    if len(values) == 0:
        return (float("nan"), float("nan"))
    means = np.array([rng.choice(values, size=len(values), replace=True).mean()
                      for _ in range(n_boot)])
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def run(df: pd.DataFrame, test_size: int = 150, seed: int = 0,
        ml_refit_every: int = 30, include_ml: bool = True) -> dict:
    n = len(df)
    start = max(60, n - test_size)
    test_idx = list(range(start, n))
    rng = np.random.default_rng(seed)

    strat_names = list(fourd_strategies.STRATEGIES.keys())
    ml_keys = fourd_ml.ML_MODEL_KEYS if include_ml else []
    match_series: Dict[str, List[int]] = {s: [] for s in strat_names}
    hit_any: Dict[str, List[int]] = {s: [] for s in strat_names}
    for k in ml_keys:
        match_series[k] = []
        hit_any[k] = []

    ml_models: Dict[str, Optional[FourDMLPredictor]] = {k: None for k in ml_keys}

    for step, t in enumerate(test_idx):
        history = df.iloc[:t]
        actual_first = df.iloc[t]["first"]
        actual_all = set(df.iloc[t]["all_numbers"])

        for s in strat_names:
            step_rng = np.random.default_rng([seed, t, fourd_strategies.STRATEGY_INDEX[s]])
            pred = fourd_strategies.STRATEGIES[s](history, step_rng)["number"]
            match_series[s].append(_digit_matches(pred, actual_first))
            hit_any[s].append(1 if pred in actual_all else 0)

        for k in ml_keys:
            if ml_models[k] is None or step % ml_refit_every == 0:
                ml_models[k] = FourDMLPredictor(k).fit(history)
            pred = ml_models[k].predict_next(history)["number"]
            match_series[k].append(_digit_matches(pred, actual_first))
            hit_any[k].append(1 if pred in actual_all else 0)

    baseline = fc.EXPECTED_RANDOM_DIGIT_MATCHES
    n_tested = sum(1 for s in match_series if s != "random")
    sig_threshold = ALPHA / max(n_tested, 1)

    results = []
    for s, series in match_series.items():
        arr = np.array(series, dtype=float)
        lo, hi = _bootstrap_ci(arr, rng)
        if s == "random" or len(arr) < 3:
            p_one_sided = None
        elif arr.std(ddof=1) == 0:
            p_one_sided = 0.0 if arr.mean() > baseline else 1.0
        else:
            tstat, p_two = stats.ttest_1samp(arr, baseline)
            p_one_sided = (p_two / 2) if tstat > 0 else (1 - p_two / 2)
        beats = bool(s != "random" and arr.mean() > baseline
                     and p_one_sided is not None and p_one_sided < sig_threshold)
        label = (fourd_strategies.STRATEGY_LABELS[s])
        results.append({
            "strategy": s, "label": label,
            "mean_matches": round(float(arr.mean()), 4),
            "ci_low": round(lo, 4), "ci_high": round(hi, 4),
            "hit_any_rate": round(float(np.mean(hit_any[s])), 5),
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
        "exact_hit_random": round(fc.NUMBERS_PER_DRAW / 10000, 5),
        "sig_threshold": round(sig_threshold, 4),
        "results": results,
        "any_beats_random": any_beats,
        "verdict": (
            "No strategy beats the random baseline (0.4 matched digits) at a "
            "statistically significant level. Consistent with an unpredictable, "
            "fair lottery - exactly as expected."
            if not any_beats else
            "A strategy edged past the baseline in this sample. With several "
            "strategies on finite data, occasional false positives are expected "
            "and do not replicate - they are noise, not an edge."
        ),
        "disclaimer": fc.DISCLAIMER,
    }
