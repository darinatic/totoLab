"""Raw 4D draw history endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import deps, fourd_analysis

router = APIRouter(prefix="/draws", tags=["4d-draws"])


@router.get("")
def list_draws(
    df=Depends(deps.get_fourd_draws),
    limit: int = Query(30, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total = len(df)
    page = df.iloc[::-1].iloc[offset: offset + limit]
    items = [
        {
            "draw_no": int(r["draw_no"]),
            "draw_date": r["draw_date"],
            "first": r["first"], "second": r["second"], "third": r["third"],
            "starters": list(r["starters"]),
            "consolations": list(r["consolations"]),
        }
        for _, r in page.iterrows()
    ]
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/latest")
def latest(df=Depends(deps.get_fourd_draws)):
    return fourd_analysis.latest_draw(df)
