"""Fairness tests, predictions, and the backtest - the honest core endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import backtest, config, deps, fairness, ml, strategies

router = APIRouter(tags=["insights"])


@router.get("/fairness")
def fairness_tests(df=Depends(deps.get_draws)):
    return fairness.run_all(df)


@router.get("/strategies")
def list_strategies():
    return {
        "strategies": [
            {"key": k, "label": strategies.STRATEGY_LABELS[k],
             "blurb": strategies.STRATEGY_BLURBS[k]}
            for k in strategies.STRATEGY_LABELS
        ],
        "disclaimer": config.DISCLAIMER,
    }


@router.get("/predict")
def predict(
    df=Depends(deps.get_draws),
    strategy: str = Query("all"),
    seed: int | None = Query(None),
    count: int = Query(config.PICK, ge=config.PICK, le=12),
    sets: int = Query(1, ge=1, le=10),
):
    """Next-draw picks. `strategy=all` returns every strategy including ML.

    `count` = numbers per set (6-12, i.e. Toto System bets); `sets` = how many
    independent sets per strategy.
    """
    def one(key: str) -> dict:
        if key in ml.ML_MODEL_KEYS:
            return ml.predict(key, df, seed=seed, count=count, sets=sets)
        return strategies.predict(key, df, seed=seed, count=count, sets=sets)

    if strategy == "all":
        keys = list(strategies.STRATEGIES.keys()) + ml.ML_MODEL_KEYS
        picks = [one(k) for k in keys]
    else:
        if strategy not in strategies.STRATEGIES and strategy not in ml.ML_MODEL_KEYS:
            raise HTTPException(404, f"Unknown strategy '{strategy}'")
        picks = [one(strategy)]

    return {
        "next_draw_after": df.iloc[-1]["draw_date"],
        "count": count,
        "sets": sets,
        "picks": picks,
        "disclaimer": config.DISCLAIMER,
    }


@router.get("/backtest")
def run_backtest(
    df=Depends(deps.get_draws),
    test_size: int = Query(150, ge=20, le=500),
    include_ml: bool = Query(True),
    seed: int = Query(0),
):
    return backtest.run(df, test_size=test_size, seed=seed, include_ml=include_ml)
