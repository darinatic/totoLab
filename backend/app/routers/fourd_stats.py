"""4D descriptive statistics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import deps, fourd_analysis

router = APIRouter(prefix="/stats", tags=["4d-stats"])


@router.get("/digit-frequency")
def digit_frequency(df=Depends(deps.get_fourd_draws), source: str = Query("all")):
    return {"n_draws": len(df), "source": source,
            "positions": fourd_analysis.digit_frequency_by_position(df, source)}


@router.get("/overall-digits")
def overall_digits(df=Depends(deps.get_fourd_draws)):
    return {"digits": fourd_analysis.overall_digit_frequency(df)}


@router.get("/hotcold")
def hotcold(df=Depends(deps.get_fourd_draws)):
    return fourd_analysis.hot_cold_digits(df)


@router.get("/sums")
def sums(df=Depends(deps.get_fourd_draws)):
    return fourd_analysis.digit_sum_distribution(df)


@router.get("/repeats")
def repeats(df=Depends(deps.get_fourd_draws)):
    return fourd_analysis.repeats_from_previous(df)


@router.get("/patterns")
def patterns(df=Depends(deps.get_fourd_draws)):
    return {"patterns": fourd_analysis.first_prize_patterns(df)}


@router.get("/most-drawn")
def most_drawn(df=Depends(deps.get_fourd_draws), top: int = 20):
    return {"numbers": fourd_analysis.most_drawn_numbers(df, top=top)}


@router.get("/rolling")
def rolling(df=Depends(deps.get_fourd_draws),
            position: int = Query(0, ge=0, le=3),
            digit: int = Query(0, ge=0, le=9)):
    return {"position": position, "digit": digit,
            "expected_rate": round(1 / 10, 3),
            "rolling": fourd_analysis.rolling_digit_rate(df, position, digit)}


@router.get("/number/{number}")
def number_detail(number: str, df=Depends(deps.get_fourd_draws)):
    return fourd_analysis.number_detail(df, number)
