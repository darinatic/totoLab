"""Tests for the lookback-window filter."""
import pandas as pd

from app import backtest, deps, fourd_backtest


def _dated_df(dates):
    return pd.DataFrame({"draw_date": dates, "numbers": [[1, 2, 3, 4, 5, 6]] * len(dates)})


def test_apply_window_all_passthrough():
    df = _dated_df(["2024-01-01", "2025-01-01", "2026-07-01"])
    assert len(deps.apply_window(df, "all")) == 3


def test_apply_window_filters_to_recent():
    dates = pd.date_range("2024-01-01", "2026-07-01", freq="MS").strftime("%Y-%m-%d").tolist()
    df = _dated_df(dates)
    # cutoff anchored to the latest date (2026-07-01)
    w6 = deps.apply_window(df, "6m")
    assert all(d >= "2026-01-01" for d in w6["draw_date"])
    assert len(w6) == 7   # Jan..Jul 2026
    assert len(deps.apply_window(df, "3m")) == 4   # Apr..Jul 2026


def test_apply_window_empty_is_safe():
    assert deps.apply_window(pd.DataFrame({"draw_date": []}), "6m").empty


def test_backtest_small_window_still_runs(draws_df):
    small = draws_df.iloc[-30:].reset_index(drop=True)
    res = backtest.run(small, test_size=150, include_ml=False, seed=0)
    assert res["test_size"] > 0          # non-empty test set despite tiny window
    assert res["small_sample"] is True
    assert res["any_beats_random"] is False


def test_fourd_backtest_small_window_still_runs(fourd_df):
    small = fourd_df.iloc[-30:].reset_index(drop=True)
    res = fourd_backtest.run(small, test_size=150, include_ml=False, seed=0)
    assert res["test_size"] > 0
    assert res["small_sample"] is True
    assert res["any_beats_random"] is False
