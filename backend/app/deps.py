"""Shared FastAPI dependencies + a small cache for the draws DataFrame."""
from __future__ import annotations

import pandas as pd
from fastapi import HTTPException, Query

from . import config, db, fourd_db

# Game-keyed cache of the FULL (era-filtered) DataFrame; window slices are derived
# cheaply per request rather than cached separately.
_cache: dict[str, pd.DataFrame] = {}


def invalidate_cache() -> None:
    _cache.clear()


def apply_window(df: pd.DataFrame, window: str) -> pd.DataFrame:
    """Return the slice of `df` within a lookback window preset.

    The cutoff is anchored to the data's latest draw date, so "6m" means six
    months of real draws. `draw_date` is ISO text, so the compare is lexicographic.
    """
    months = config.WINDOW_MONTHS.get(window)
    if not months or df.empty:
        return df
    latest = pd.Timestamp(df["draw_date"].max())
    cutoff = (latest - pd.DateOffset(months=months)).strftime("%Y-%m-%d")
    return df[df["draw_date"] >= cutoff]


def get_draws(window: str = Query("all"), era_only: bool = True) -> pd.DataFrame:
    """Load Toto draws (cached), sliced to `window`. 503 if the DB is unseeded."""
    key = f"toto:era={era_only}"
    if key not in _cache:
        df = db.load_draws(era_only=era_only)
        if df.empty:
            raise HTTPException(status_code=503, detail="No Toto draw data loaded yet.")
        _cache[key] = df
    return apply_window(_cache[key], window)


def get_fourd_draws(window: str = Query("all"), era_only: bool = True) -> pd.DataFrame:
    """Load 4D draws (cached), sliced to `window`. 503 if the DB is unseeded."""
    key = f"4d:era={era_only}"
    if key not in _cache:
        df = fourd_db.load_fourd_draws(era_only=era_only)
        if df.empty:
            raise HTTPException(status_code=503, detail="No 4D draw data loaded yet.")
        _cache[key] = df
    return apply_window(_cache[key], window)
