"""Randomness / fairness tests for 4D - the honest heart.

If the draw is fair, every digit 0-9 is equally likely in every position and
successive draws are independent. Same `scipy`-backed framework as the Toto
`fairness` module, with digit-shaped inputs.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

from . import fourd_config as fc

ALPHA = 0.05


def chi_square_digits(df: pd.DataFrame) -> dict:
    """Chi-square GOF: are digits 0-9 uniform across the First prize's positions?"""
    digits = [d for digs in df["first_digits"] for d in digs]
    counts = Counter(digits)
    observed = np.array([counts.get(d, 0) for d in fc.DIGITS], dtype=float)
    expected = np.full(fc.N_DIGITS, observed.sum() / fc.N_DIGITS)
    chi2, p = stats.chisquare(observed, expected)
    return {
        "test": "Chi-square goodness-of-fit (uniformity of digits 0-9)",
        "statistic": round(float(chi2), 3),
        "df": fc.N_DIGITS - 1,
        "p_value": round(float(p), 4),
        "passes": bool(p > ALPHA),
        "verdict": (
            "Consistent with a fair draw - no digit is significantly over- or "
            "under-represented."
            if p > ALPHA else
            "Digits deviate from uniform more than chance would suggest."
        ),
    }


def chi_square_by_position(df: pd.DataFrame) -> dict:
    """Chi-square per position - flags if any single position is biased."""
    worst_p = 1.0
    per = []
    for pos in range(fc.POSITIONS):
        counts = Counter(digs[pos] for digs in df["first_digits"])
        observed = np.array([counts.get(d, 0) for d in fc.DIGITS], dtype=float)
        expected = np.full(fc.N_DIGITS, observed.sum() / fc.N_DIGITS)
        _, p = stats.chisquare(observed, expected)
        per.append({"position": pos + 1, "p_value": round(float(p), 4)})
        worst_p = min(worst_p, float(p))
    # Bonferroni across the 4 positions
    passes = worst_p > ALPHA / fc.POSITIONS
    return {
        "test": "Chi-square per position (each digit slot uniform)",
        "positions": per,
        "p_value": round(worst_p, 4),
        "passes": bool(passes),
        "verdict": ("Every position looks uniform." if passes
                    else "At least one position deviates from uniform."),
    }


def runs_test_parity(df: pd.DataFrame) -> dict:
    """Runs test on the parity of the First prize's digit sum."""
    seq = np.array([sum(digs) % 2 for digs in df["first_digits"]])
    n1 = int(seq.sum()); n0 = int(len(seq) - n1); n = n0 + n1
    runs = 1 + int((seq[1:] != seq[:-1]).sum()) if len(seq) > 1 else 1
    if n0 == 0 or n1 == 0:
        return {"test": "Runs test (parity of First-prize digit sum)", "runs": runs,
                "p_value": None, "passes": True, "verdict": "Not enough variation to test."}
    exp = 1 + 2 * n0 * n1 / n
    var = (2 * n0 * n1 * (2 * n0 * n1 - n)) / (n * n * (n - 1))
    z = (runs - exp) / np.sqrt(var) if var > 0 else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "test": "Runs test (parity of First-prize digit sum)",
        "runs": runs, "expected_runs": round(float(exp), 2), "z": round(float(z), 3),
        "p_value": round(float(p), 4), "passes": bool(p > ALPHA),
        "verdict": ("No significant serial pattern across draws." if p > ALPHA
                    else "Draws show serial clustering beyond chance."),
    }


def autocorrelation_sum(df: pd.DataFrame, lag: int = 1) -> dict:
    """Lag-`lag` autocorrelation of the First prize's digit sum."""
    s = np.array([sum(digs) for digs in df["first_digits"]], dtype=float)
    if len(s) <= lag + 1:
        return {"test": f"Autocorrelation (lag {lag}) of digit sums", "r": None,
                "p_value": None, "passes": True, "verdict": "Not enough data."}
    r, p = stats.pearsonr(s[:-lag], s[lag:])
    return {
        "test": f"Autocorrelation (lag {lag}) of digit sums",
        "r": round(float(r), 4), "p_value": round(float(p), 4), "passes": bool(p > ALPHA),
        "verdict": ("No significant correlation between consecutive draws - as expected "
                    "for independent random events." if p > ALPHA
                    else "Consecutive draws are correlated beyond chance."),
    }


def run_all(df: pd.DataFrame) -> dict:
    tests = [chi_square_digits(df), chi_square_by_position(df),
             runs_test_parity(df), autocorrelation_sum(df, lag=1)]
    return {
        "n_draws": len(df),
        "tests": tests,
        "overall_passes": all(t["passes"] for t in tests),
        "disclaimer": fc.DISCLAIMER,
    }
