from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.ml.model import model_service
from backend.app.schemas.ticket import TicketStats
from backend.app.services.ticket_service import TicketService

router = APIRouter(prefix="/api", tags=["Analytics & Metrics"])


@router.get(
    "/stats",
    response_model=TicketStats,
    summary="Get aggregated dashboard statistics",
)
async def get_stats(db: AsyncSession = Depends(get_db)) -> TicketStats:
    """Return counts grouped by status, category, priority, and human feedback metrics."""
    stats = await TicketService.get_stats(db)
    return TicketStats.model_validate(stats)


@router.get(
    "/model/metrics",
    summary="Get model training evaluation metrics",
)
async def get_model_metrics() -> dict[str, Any]:
    """Return the evaluation metrics produced by ml/train.py on the held-out test set."""
    metrics = model_service.get_metrics()
    if metrics is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model metrics unavailable. Run `python ml/train.py`.",
        )
    return metrics
