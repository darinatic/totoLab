"""Shared pytest fixtures."""
import numpy as np
import pandas as pd
import pytest


def _make_df(n_draws: int = 200, seed: int = 42) -> pd.DataFrame:
    """A synthetic but well-formed draw history (uniform random 6/49)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_draws):
        nums = sorted(int(x) for x in rng.choice(range(1, 50), size=6, replace=False))
        add = int(rng.choice([x for x in range(1, 50) if x not in nums]))
        rows.append({
            "draw_no": 1000 + i,
            "draw_date": f"2020-{1 + i % 12:02d}-{1 + i % 28:02d}",
            "n1": nums[0], "n2": nums[1], "n3": nums[2],
            "n4": nums[3], "n5": nums[4], "n6": nums[5],
            "additional": add,
            "numbers": nums,
            "all_numbers": nums + [add],
        })
    return pd.DataFrame(rows)


@pytest.fixture
def draws_df():
    return _make_df()


def _make_fourd_df(n_draws: int = 300, seed: int = 7, bias_pos0: int | None = None):
    """A synthetic but well-formed 4D history (uniform random digits).

    If `bias_pos0` is set, position 0 of the First prize is always that digit
    (used to check fairness tests actually detect bias).
    """
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_draws):
        def num():
            return "".join(str(int(x)) for x in rng.integers(0, 10, size=4))
        nums = set()
        while len(nums) < 23:
            nums.add(num())
        nums = list(nums)
        first = nums[0]
        if bias_pos0 is not None:
            first = str(bias_pos0) + first[1:]
            nums[0] = first
        rows.append({
            "draw_no": 5000 + i,
            "draw_date": f"2020-{1 + i % 12:02d}-{1 + i % 28:02d}",
            "first": first, "second": nums[1], "third": nums[2],
            "starters": nums[3:13], "consolations": nums[13:23],
            "all_numbers": nums,
            "first_digits": [int(c) for c in first],
        })
    return pd.DataFrame(rows)


@pytest.fixture
def fourd_df():
    return _make_fourd_df()
