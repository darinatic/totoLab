"""Descriptive stats + fairness math."""
import pandas as pd
import pytest
from scipy import stats as scipy_stats

from app import analysis, fairness


def _tiny_df():
    # two hand-checkable draws
    rows = [
        {"draw_no": 1, "draw_date": "2020-01-01",
         "n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "additional": 7,
         "numbers": [1, 2, 3, 4, 5, 6], "all_numbers": [1, 2, 3, 4, 5, 6, 7]},
        {"draw_no": 2, "draw_date": "2020-01-04",
         "n1": 1, "n2": 2, "n3": 10, "n4": 20, "n5": 30, "n6": 40, "additional": 8,
         "numbers": [1, 2, 10, 20, 30, 40], "all_numbers": [1, 2, 10, 20, 30, 40, 8]},
    ]
    return pd.DataFrame(rows)


def test_frequency_counts_hand_checked():
    df = _tiny_df()
    freq = {r["number"]: r["count"] for r in analysis.frequency(df)}
    assert freq[1] == 2   # appears in both draws
    assert freq[2] == 2
    assert freq[3] == 1
    assert freq[40] == 1
    assert freq[49] == 0
    assert sum(freq.values()) == 12  # 6 numbers * 2 draws


def test_odd_even_and_sums():
    df = _tiny_df()
    s = analysis.sums(df)
    assert s["min"] == 21   # 1+2+3+4+5+6
    assert s["max"] == 103  # 1+2+10+20+30+40
    oe = analysis.odd_even(df)
    assert sum(r["count"] for r in oe) == 2


def test_number_detail_partners():
    df = _tiny_df()
    d = analysis.number_detail(df, 1)
    assert d["appearances"] == 2
    partners = {p["number"]: p["count"] for p in d["top_partners"]}
    assert partners[2] == 2  # 1 and 2 always appear together here


def test_chi_square_matches_scipy(draws_df):
    from collections import Counter
    res = fairness.chi_square_uniform(draws_df)
    counts = Counter(n for row in draws_df["numbers"] for n in row)
    observed = [counts.get(n, 0) for n in range(1, 50)]
    exp = [sum(observed) / 49] * 49
    chi2, p = scipy_stats.chisquare(observed, exp)
    assert res["statistic"] == pytest.approx(chi2, abs=1e-3)
    assert res["df"] == 48


def test_fair_data_passes_randomness(draws_df):
    # synthetic uniform data should not be flagged as non-random
    res = fairness.run_all(draws_df)
    assert res["overall_passes"] is True
