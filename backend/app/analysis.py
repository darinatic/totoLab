"""Descriptive statistics over the draw history.

Every function takes the draws DataFrame from `db.load_draws` and returns plain
JSON-serialisable dicts/lists. None of this predicts anything - it just describes
what has happened.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Dict, List

import pandas as pd

from . import config

MAIN_COLS = ["n1", "n2", "n3", "n4", "n5", "n6"]


def _main_number_series(df: pd.DataFrame) -> List[int]:
    return [n for row in df["numbers"] for n in row]


def frequency(df: pd.DataFrame) -> List[dict]:
    """Per-number appearance count among the 6 main numbers, plus hot/cold rank.

    With N draws and 6 of 49 drawn each time, the fair expected count is
    6*N/49. `deviation` is observed minus expected.
    """
    counts = Counter(_main_number_series(df))
    n_draws = len(df)
    expected = config.PICK * n_draws / config.POOL_SIZE
    rows = []
    for num in config.POOL:
        c = counts.get(num, 0)
        rows.append(
            {
                "number": num,
                "count": c,
                "expected": round(expected, 2),
                "deviation": round(c - expected, 2),
            }
        )
    ranked = sorted(rows, key=lambda r: r["count"], reverse=True)
    for rank, r in enumerate(ranked, start=1):
        r["rank"] = rank
    return sorted(rows, key=lambda r: r["number"])


def gaps(df: pd.DataFrame) -> List[dict]:
    """For each number: draws since it last appeared ("overdue") + average gap."""
    n_draws = len(df)
    last_seen: Dict[int, int] = {}
    gap_lists: Dict[int, List[int]] = {n: [] for n in config.POOL}
    for idx, row in enumerate(df["numbers"]):
        for num in row:
            if num in last_seen:
                gap_lists[num].append(idx - last_seen[num])
            last_seen[num] = idx
    out = []
    for num in config.POOL:
        seen_idx = last_seen.get(num)
        current_gap = (n_draws - 1 - seen_idx) if seen_idx is not None else n_draws
        gl = gap_lists[num]
        out.append(
            {
                "number": num,
                "current_gap": current_gap,
                "avg_gap": round(sum(gl) / len(gl), 2) if gl else None,
                "max_gap": max(gl) if gl else None,
            }
        )
    return out


def pairs(df: pd.DataFrame, top: int = 30) -> List[dict]:
    """Most frequently co-occurring number pairs among the main numbers."""
    counter: Counter = Counter()
    for row in df["numbers"]:
        for a, b in combinations(sorted(row), 2):
            counter[(a, b)] += 1
    return [
        {"pair": [a, b], "count": c}
        for (a, b), c in counter.most_common(top)
    ]


def sums(df: pd.DataFrame) -> dict:
    """Distribution of the sum of the 6 main numbers."""
    s = df["numbers"].apply(sum)
    hist = Counter((int(v) // 10) * 10 for v in s)  # 10-wide buckets
    return {
        "min": int(s.min()),
        "max": int(s.max()),
        "mean": round(float(s.mean()), 1),
        "median": float(s.median()),
        "histogram": [
            {"bucket": f"{b}-{b + 9}", "count": hist[b]}
            for b in sorted(hist)
        ],
    }


def odd_even(df: pd.DataFrame) -> List[dict]:
    """Distribution of odd/even splits (e.g. how often 3 odd + 3 even)."""
    counter = Counter(sum(1 for n in row if n % 2 == 1) for row in df["numbers"])
    total = len(df)
    return [
        {
            "odd": k,
            "even": config.PICK - k,
            "count": counter.get(k, 0),
            "pct": round(100 * counter.get(k, 0) / total, 1),
        }
        for k in range(config.PICK + 1)
    ]


def low_high(df: pd.DataFrame) -> List[dict]:
    """Distribution of low(1-24)/high(25-49) splits."""
    counter = Counter(sum(1 for n in row if n <= 24) for row in df["numbers"])
    total = len(df)
    return [
        {
            "low": k,
            "high": config.PICK - k,
            "count": counter.get(k, 0),
            "pct": round(100 * counter.get(k, 0) / total, 1),
        }
        for k in range(config.PICK + 1)
    ]


def decades(df: pd.DataFrame) -> List[dict]:
    """How many main numbers fall in each 1-10, 11-20, ... band."""
    bands = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 49)]
    nums = _main_number_series(df)
    out = []
    for lo, hi in bands:
        c = sum(1 for n in nums if lo <= n <= hi)
        out.append({"band": f"{lo}-{hi}", "count": c})
    return out


def repeats_from_previous(df: pd.DataFrame) -> dict:
    """How many numbers each draw shares with the immediately preceding draw.

    For independent draws the expected overlap is 6 * 6/49 ≈ 0.735.
    """
    counter: Counter = Counter()
    prev = None
    for row in df["numbers"]:
        if prev is not None:
            counter[len(set(row) & set(prev))] += 1
        prev = row
    total = sum(counter.values()) or 1
    return {
        "expected_mean": round(config.PICK * config.PICK / config.POOL_SIZE, 3),
        "distribution": [
            {"repeats": k, "count": counter.get(k, 0),
             "pct": round(100 * counter.get(k, 0) / total, 1)}
            for k in range(config.PICK + 1)
        ],
    }


def consecutive_numbers(df: pd.DataFrame) -> dict:
    """Distribution of how many adjacent pairs (e.g. 23 & 24) each draw contains."""
    counter: Counter = Counter()
    any_consecutive = 0
    for row in df["numbers"]:
        s = set(row)
        pairs = sum(1 for n in row if (n + 1) in s)
        counter[pairs] += 1
        if pairs:
            any_consecutive += 1
    total = len(df) or 1
    return {
        "pct_with_consecutive": round(100 * any_consecutive / total, 1),
        "distribution": [
            {"pairs": k, "count": counter.get(k, 0),
             "pct": round(100 * counter.get(k, 0) / total, 1)}
            for k in range(config.PICK)
        ],
    }


def wait_time_distribution(df: pd.DataFrame) -> dict:
    """Histogram of gaps (draws) between successive appearances of any number.

    A memoryless process gives a roughly geometric distribution with mean 49/6.
    """
    last_seen: Dict[int, int] = {}
    gaps: List[int] = []
    for idx, row in enumerate(df["numbers"]):
        for num in row:
            if num in last_seen:
                gaps.append(idx - last_seen[num])
            last_seen[num] = idx
    counter = Counter(gaps)
    cap = 40
    hist = []
    for g in range(1, cap + 1):
        hist.append({"gap": g, "count": counter.get(g, 0)})
    tail = sum(c for g, c in counter.items() if g > cap)
    hist.append({"gap": f"{cap + 1}+", "count": tail})
    return {
        "expected_mean": round(config.POOL_SIZE / config.PICK, 2),
        "observed_mean": round(sum(gaps) / len(gaps), 2) if gaps else None,
        "histogram": hist,
    }


def rolling_frequency(df: pd.DataFrame, number: int, window: int = 50) -> List[dict]:
    """Rolling appearance rate of one number over a trailing window of draws.

    For a fair draw this hovers around 6/49 ≈ 0.122 with no trend.
    """
    appears = [1 if number in row else 0 for row in df["numbers"]]
    dates = list(df["draw_date"])
    out = []
    if len(appears) < window:
        return out
    running = sum(appears[:window])
    out.append({"draw_date": dates[window - 1], "rate": round(running / window, 4)})
    for i in range(window, len(appears)):
        running += appears[i] - appears[i - window]
        out.append({"draw_date": dates[i], "rate": round(running / window, 4)})
    return out


def number_detail(df: pd.DataFrame, number: int) -> dict:
    """Everything about a single number: frequency, gaps, top partners."""
    freq = next(r for r in frequency(df) if r["number"] == number)
    gap = next(r for r in gaps(df) if r["number"] == number)
    partner: Counter = Counter()
    appearances = []
    for _, row in df.iterrows():
        if number in row["numbers"]:
            appearances.append(row["draw_date"])
            for other in row["numbers"]:
                if other != number:
                    partner[other] += 1
    return {
        "number": number,
        "frequency": freq,
        "gaps": gap,
        "top_partners": [
            {"number": n, "count": c} for n, c in partner.most_common(6)
        ],
        "appearances": len(appearances),
        "last_seen": appearances[-1] if appearances else None,
        "rolling": rolling_frequency(df, number),
        "expected_rate": round(config.PICK / config.POOL_SIZE, 4),
    }


def latest_draw(df: pd.DataFrame) -> dict:
    row = df.iloc[-1]
    return {
        "draw_no": int(row["draw_no"]),
        "draw_date": row["draw_date"],
        "numbers": [int(n) for n in row["numbers"]],
        "additional": int(row["additional"]),
    }
