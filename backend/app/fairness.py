"""Randomness / fairness tests - the honest heart of the project.

If the draw is fair, every number is equally likely and successive draws are
independent. These tests check exactly that and report a plain-language verdict.
A fair lottery should PASS (i.e. we fail to reject the null of randomness).
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

from . import config
from .analysis import _main_number_series

ALPHA = 0.05


def chi_square_uniform(df: pd.DataFrame) -> dict:
    """Chi-square goodness-of-fit: are all 49 numbers equally likely?"""
    counts = Counter(_main_number_series(df))
    observed = np.array([counts.get(n, 0) for n in config.POOL], dtype=float)
    expected = np.full(config.POOL_SIZE, observed.sum() / config.POOL_SIZE)
    chi2, p = stats.chisquare(observed, expected)
    return {
        "test": "Chi-square goodness-of-fit (uniformity of numbers 1-49)",
        "statistic": round(float(chi2), 3),
        "df": config.POOL_SIZE - 1,
        "p_value": round(float(p), 4),
        "passes": bool(p > ALPHA),
        "verdict": (
            "Consistent with a fair draw - no number is significantly over- or "
            "under-represented."
            if p > ALPHA
            else "Numbers deviate from uniform more than chance would suggest."
        ),
    }


def runs_test_parity(df: pd.DataFrame) -> dict:
    """Wald-Wolfowitz runs test on the parity of each draw's sum.

    Treats each draw's sum as odd/even and checks whether the sequence of
    odd/even outcomes clusters (non-random) or alternates randomly.
    """
    seq = np.array([sum(row) % 2 for row in df["numbers"]])
    n1 = int(seq.sum())            # odd sums
    n0 = int(len(seq) - n1)        # even sums
    runs = 1 + int((seq[1:] != seq[:-1]).sum()) if len(seq) > 1 else 1
    n = n0 + n1
    if n0 == 0 or n1 == 0:
        return {
            "test": "Runs test (parity of draw sums)",
            "runs": runs, "p_value": None, "passes": True,
            "verdict": "Not enough variation to test.",
        }
    exp_runs = 1 + 2 * n0 * n1 / n
    var_runs = (2 * n0 * n1 * (2 * n0 * n1 - n)) / (n * n * (n - 1))
    z = (runs - exp_runs) / np.sqrt(var_runs) if var_runs > 0 else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "test": "Runs test (parity of draw sums)",
        "runs": runs,
        "expected_runs": round(float(exp_runs), 2),
        "z": round(float(z), 3),
        "p_value": round(float(p), 4),
        "passes": bool(p > ALPHA),
        "verdict": (
            "Sequence of draws shows no significant serial pattern."
            if p > ALPHA
            else "Draws show serial clustering beyond chance."
        ),
    }


def autocorrelation_sum(df: pd.DataFrame, lag: int = 1) -> dict:
    """Lag-`lag` autocorrelation of the draw sum: does one draw predict the next?"""
    s = np.array([sum(row) for row in df["numbers"]], dtype=float)
    if len(s) <= lag + 1:
        return {"test": f"Autocorrelation (lag {lag}) of draw sums",
                "r": None, "p_value": None, "passes": True,
                "verdict": "Not enough data."}
    a, b = s[:-lag], s[lag:]
    r, p = stats.pearsonr(a, b)
    return {
        "test": f"Autocorrelation (lag {lag}) of draw sums",
        "r": round(float(r), 4),
        "p_value": round(float(p), 4),
        "passes": bool(p > ALPHA),
        "verdict": (
            "No significant correlation between consecutive draws - as expected "
            "for independent random events."
            if p > ALPHA
            else "Consecutive draws are correlated beyond chance."
        ),
    }


def run_all(df: pd.DataFrame) -> dict:
    tests = [
        chi_square_uniform(df),
        runs_test_parity(df),
        autocorrelation_sum(df, lag=1),
    ]
    return {
        "n_draws": len(df),
        "tests": tests,
        "overall_passes": all(t["passes"] for t in tests),
        "disclaimer": config.DISCLAIMER,
    }
