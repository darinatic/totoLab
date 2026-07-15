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

from . import (backtest, config, db, fourd_backtest, fourd_config, fourd_db,
               fourd_ingest, ingest)

# Must match the frontend's default Reality Check settings.
DEFAULT_TEST_SIZE = 150
DEFAULT_INCLUDE_ML = True
DEFAULT_SEED = 0


def _write(out: Path, result: dict, last_draw_no: int) -> Path:
    result["precomputed"] = True
    result["generated_from_draw"] = int(last_draw_no)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return out


def generate(out: Path | None = None, df=None) -> Path:
    """Precompute the Toto default backtest."""
    out = Path(out or config.PRECOMPUTE_BACKTEST)
    if df is None:
        db.init_db()
        ingest.seed_if_empty()
        df = db.load_draws()
    result = backtest.run(df, test_size=DEFAULT_TEST_SIZE,
                          include_ml=DEFAULT_INCLUDE_ML, seed=DEFAULT_SEED)
    return _write(out, result, df.iloc[-1]["draw_no"])


def generate_fourd(out: Path | None = None, df=None) -> Path:
    """Precompute the 4D default backtest."""
    out = Path(out or fourd_config.FOURD_PRECOMPUTE_BACKTEST)
    if df is None:
        fourd_db.init_db()
        fourd_ingest.seed_if_empty()
        df = fourd_db.load_fourd_draws()
    result = fourd_backtest.run(df, test_size=DEFAULT_TEST_SIZE,
                                include_ml=DEFAULT_INCLUDE_ML, seed=DEFAULT_SEED)
    return _write(out, result, df.iloc[-1]["draw_no"])


if __name__ == "__main__":  # python -m app.precompute [--game toto|4d|both]
    parser = argparse.ArgumentParser(description="Precompute default backtest JSON")
    parser.add_argument("--game", choices=["toto", "4d", "both"], default="both")
    parser.add_argument("--out", default=None, help="output path (single game only)")
    args = parser.parse_args()
    if args.game in ("toto", "both"):
        print(f"Wrote {generate(args.out if args.game == 'toto' else None)}")
    if args.game in ("4d", "both"):
        print(f"Wrote {generate_fourd(args.out if args.game == '4d' else None)}")
