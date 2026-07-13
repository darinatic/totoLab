"""Shared FastAPI dependencies + a small cache for the draws DataFrame."""
from __future__ import annotations

import pandas as pd
from fastapi import HTTPException

from . import db

_cache: dict[str, pd.DataFrame] = {}


def invalidate_cache() -> None:
    _cache.clear()


def get_draws(era_only: bool = True) -> pd.DataFrame:
    """Load draws (cached). Raises 503 if the DB has not been seeded."""
    key = f"era={era_only}"
    if key not in _cache:
        df = db.load_draws(era_only=era_only)
        if df.empty:
            raise HTTPException(status_code=503, detail="No draw data loaded yet.")
        _cache[key] = df
    return _cache[key]
