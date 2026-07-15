"""4D fairness, predictions, and backtest endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import deps, fourd_backtest, fourd_config, fourd_fairness, fourd_ml, fourd_strategies

router = APIRouter(tags=["4d-insights"])


@router.get("/fairness")
def fairness_tests(df=Depends(deps.get_fourd_draws)):
    return fourd_fairness.run_all(df)


@router.get("/strategies")
def list_strategies():
    return {
        "strategies": [
            {"key": k, "label": fourd_strategies.STRATEGY_LABELS[k],
             "blurb": fourd_strategies.STRATEGY_BLURBS[k]}
            for k in fourd_strategies.STRATEGY_LABELS
        ],
        "disclaimer": fourd_config.DISCLAIMER,
    }


@router.get("/predict")
def predict(
    df=Depends(deps.get_fourd_draws),
    strategy: str = Query("all"),
    seed: int | None = Query(None),
    sets: int = Query(1, ge=1, le=10),
):
    all_keys = list(fourd_strategies.STRATEGIES.keys()) + fourd_ml.ML_MODEL_KEYS
    if strategy == "all":
        picks = [fourd_strategies.predict(k, df, seed=seed, sets=sets) for k in all_keys]
    else:
        if strategy not in all_keys:
            raise HTTPException(404, f"Unknown strategy '{strategy}'")
        picks = [fourd_strategies.predict(strategy, df, seed=seed, sets=sets)]
    return {
        "next_draw_after": df.iloc[-1]["draw_date"],
        "sets": sets,
        "picks": picks,
        "disclaimer": fourd_config.DISCLAIMER,
    }


@router.get("/backtest")
def run_backtest(
    df=Depends(deps.get_fourd_draws),
    test_size: int = Query(150, ge=20, le=400),
    include_ml: bool = Query(True),
    seed: int = Query(0),
):
    return fourd_backtest.run(df, test_size=test_size, seed=seed, include_ml=include_ml)
