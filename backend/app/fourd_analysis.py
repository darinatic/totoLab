"""Descriptive statistics over the 4D draw history.

Everything operates on the per-draw DataFrame from `fourd_db.load_fourd_draws`
(columns include `all_numbers` = the 23 winning 4-digit strings and
`first_digits` = the four ints of the First prize). Returns plain
JSON-serialisable structures. None of this predicts anything.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

import pandas as pd

from . import fourd_config as fc


def _position_digits(df: pd.DataFrame, position: int, source: str) -> List[int]:
    """All digits seen at `position` across history, from 'all' 23 or the 'first'."""
    out: List[int] = []
    if source == "first":
        for digs in df["first_digits"]:
            out.append(digs[position])
    else:
        for nums in df["all_numbers"]:
            for s in nums:
                out.append(int(s[position]))
    return out


def digit_frequency_by_position(df: pd.DataFrame, source: str = "all") -> List[dict]:
    """Per position (0-3), the count of each digit 0-9 vs the fair expectation."""
    out = []
    for p in range(fc.POSITIONS):
        digits = _position_digits(df, p, source)
        counts = Counter(digits)
        total = len(digits)
        expected = total / fc.N_DIGITS if total else 0
        rows = [{
            "digit": d,
            "count": counts.get(d, 0),
            "expected": round(expected, 1),
            "deviation": round(counts.get(d, 0) - expected, 1),
        } for d in fc.DIGITS]
        out.append({"position": p, "label": f"Position {p + 1}", "digits": rows})
    return out


def overall_digit_frequency(df: pd.DataFrame) -> List[dict]:
    """Digit 0-9 frequency across all positions of all 23 numbers."""
    counts: Counter = Counter()
    for nums in df["all_numbers"]:
        for s in nums:
            for ch in s:
                counts[int(ch)] += 1
    total = sum(counts.values())
    exp = total / fc.N_DIGITS if total else 0
    return [{"digit": d, "count": counts.get(d, 0),
             "expected": round(exp, 1), "deviation": round(counts.get(d, 0) - exp, 1)}
            for d in fc.DIGITS]


def hot_cold_digits(df: pd.DataFrame) -> dict:
    """Most/least frequent digit per position (First prize)."""
    out = []
    for p in range(fc.POSITIONS):
        counts = Counter(_position_digits(df, p, "first"))
        ranked = sorted(fc.DIGITS, key=lambda d: counts.get(d, 0), reverse=True)
        out.append({"position": p, "hot": ranked[0], "cold": ranked[-1]})
    return {"by_position": out}


def digit_sum_distribution(df: pd.DataFrame) -> dict:
    """Distribution of the sum of the First prize's 4 digits (0-36)."""
    sums = [sum(digs) for digs in df["first_digits"]]
    counter = Counter(sums)
    return {
        "min": min(sums) if sums else 0,
        "max": max(sums) if sums else 0,
        "mean": round(sum(sums) / len(sums), 1) if sums else 0,
        "histogram": [{"sum": s, "count": counter.get(s, 0)} for s in range(37)],
    }


def repeats_from_previous(df: pd.DataFrame) -> dict:
    """How many digit-positions the First prize shares with the previous draw's.

    For independent draws the expected overlap is 4 * 1/10 = 0.4.
    """
    counter: Counter = Counter()
    prev = None
    for digs in df["first_digits"]:
        if prev is not None:
            counter[sum(1 for a, b in zip(digs, prev) if a == b)] += 1
        prev = digs
    total = sum(counter.values()) or 1
    return {
        "expected_mean": round(fc.EXPECTED_RANDOM_DIGIT_MATCHES, 2),
        "distribution": [{"matches": k, "count": counter.get(k, 0),
                          "pct": round(100 * counter.get(k, 0) / total, 1)}
                         for k in range(fc.POSITIONS + 1)],
    }


def first_prize_patterns(df: pd.DataFrame) -> List[dict]:
    """How often the First prize is all-different / one-pair / etc."""
    labels = {4: "All different", 3: "One pair", 2: "Two pair or triple", 1: "Quad"}
    counter: Counter = Counter()
    for digs in df["first_digits"]:
        counter[len(set(digs))] += 1
    total = len(df) or 1
    return [{"pattern": labels[u], "unique_digits": u, "count": counter.get(u, 0),
             "pct": round(100 * counter.get(u, 0) / total, 1)}
            for u in (4, 3, 2, 1)]


def most_drawn_numbers(df: pd.DataFrame, top: int = 20) -> List[dict]:
    """The 4-digit numbers that have appeared most (across all 23, all history)."""
    counter: Counter = Counter()
    for nums in df["all_numbers"]:
        for s in nums:
            counter[s] += 1
    return [{"number": n, "count": c} for n, c in counter.most_common(top)]


def rolling_digit_rate(df: pd.DataFrame, position: int, digit: int,
                       window: int = 100) -> List[dict]:
    """Rolling rate of `digit` at `position` of the First prize over a window."""
    appears = [1 if digs[position] == digit else 0 for digs in df["first_digits"]]
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


def number_detail(df: pd.DataFrame, number: str) -> dict:
    """Everything about one 4-digit number: appearances and how it landed."""
    number = str(number).zfill(4)
    appearances = []
    by_prize: Counter = Counter()
    for _, r in df.iterrows():
        for code, nums in (("1", [r["first"]]), ("2", [r["second"]]), ("3", [r["third"]]),
                           ("S", r["starters"]), ("C", r["consolations"])):
            if number in nums:
                appearances.append(r["draw_date"])
                by_prize[code] += 1
    return {
        "number": number,
        "digits": [int(c) for c in number],
        "digit_sum": sum(int(c) for c in number),
        "appearances": len(appearances),
        "last_seen": appearances[-1] if appearances else None,
        "by_prize": [{"prize_code": c, "count": by_prize.get(c, 0)} for c in fc.PRIZE_CODES],
    }


def latest_draw(df: pd.DataFrame) -> dict:
    r = df.iloc[-1]
    return {
        "draw_no": int(r["draw_no"]),
        "draw_date": r["draw_date"],
        "first": r["first"], "second": r["second"], "third": r["third"],
        "starters": list(r["starters"]), "consolations": list(r["consolations"]),
    }
