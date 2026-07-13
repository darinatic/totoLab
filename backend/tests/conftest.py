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
