"""Raw draw history endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import analysis, deps

router = APIRouter(prefix="/draws", tags=["draws"])


@router.get("")
def list_draws(
    df=Depends(deps.get_draws),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    total = len(df)
    # newest first for display
    page = df.iloc[::-1].iloc[offset: offset + limit]
    items = [
        {
            "draw_no": int(r["draw_no"]),
            "draw_date": r["draw_date"],
            "numbers": [int(n) for n in r["numbers"]],
            "additional": int(r["additional"]),
            "sum": int(sum(r["numbers"])),
        }
        for _, r in page.iterrows()
    ]
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/latest")
def latest(df=Depends(deps.get_draws)):
    return analysis.latest_draw(df)
