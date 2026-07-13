"""Descriptive statistics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from .. import analysis, config, deps

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/frequency")
def frequency(df=Depends(deps.get_draws)):
    return {"n_draws": len(df), "numbers": analysis.frequency(df)}


@router.get("/gaps")
def gaps(df=Depends(deps.get_draws)):
    return {"n_draws": len(df), "numbers": analysis.gaps(df)}


@router.get("/pairs")
def pairs(df=Depends(deps.get_draws), top: int = 30):
    return {"pairs": analysis.pairs(df, top=top)}


@router.get("/sums")
def sums(df=Depends(deps.get_draws)):
    return analysis.sums(df)


@router.get("/oddeven")
def oddeven(df=Depends(deps.get_draws)):
    return {"odd_even": analysis.odd_even(df), "low_high": analysis.low_high(df)}


@router.get("/decades")
def decades(df=Depends(deps.get_draws)):
    return {"decades": analysis.decades(df)}


@router.get("/repeats")
def repeats(df=Depends(deps.get_draws)):
    return analysis.repeats_from_previous(df)


@router.get("/consecutive")
def consecutive(df=Depends(deps.get_draws)):
    return analysis.consecutive_numbers(df)


@router.get("/waittime")
def waittime(df=Depends(deps.get_draws)):
    return analysis.wait_time_distribution(df)


@router.get("/number/{number}")
def number_detail(number: int = Path(..., ge=config.POOL_MIN, le=config.POOL_MAX),
                  df=Depends(deps.get_draws)):
    return analysis.number_detail(df, number)
