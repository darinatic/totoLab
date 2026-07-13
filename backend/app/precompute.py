"""Precompute the default backtest into a static JSON.

The walk-forward backtest (with ML retraining) is slow, so we run it once here
and write the result as a static asset the SPA loads instantly on first view.
Deterministic (seed=0), so the output only changes when the draw data changes -
the refresh-data GitHub Action regenerates and commits it alongside new draws.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import backtest, config, db, ingest

# Must match the frontend's default Reality Check settings.
DEFAULT_TEST_SIZE = 150
DEFAULT_INCLUDE_ML = True
DEFAULT_SEED = 0


def generate(out: Path | None = None, df=None) -> Path:
    out = Path(out or config.PRECOMPUTE_BACKTEST)
    if df is None:
        db.init_db()
        ingest.seed_if_empty()
        df = db.load_draws()
    result = backtest.run(
        df, test_size=DEFAULT_TEST_SIZE, include_ml=DEFAULT_INCLUDE_ML, seed=DEFAULT_SEED
    )
    result["precomputed"] = True
    result["generated_from_draw"] = int(df.iloc[-1]["draw_no"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":  # python -m app.precompute
    parser = argparse.ArgumentParser(description="Precompute the default backtest JSON")
    parser.add_argument("--out", default=None, help="output path")
    args = parser.parse_args()
    path = generate(args.out)
    print(f"Wrote {path}")
