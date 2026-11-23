from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.metrics import get_prometheus_metrics
from backend.app.ml.model import model_service
from backend.app.schemas.ticket import HealthResponse

router = APIRouter(tags=["Monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check database connectivity and ML model readiness."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    model_loaded = model_service.is_loaded
    overall_status = "healthy" if (db_status == "connected" and model_loaded) else "degraded"
    status_code = (
        status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    content = HealthResponse(
        status=overall_status,
        database=db_status,
        model_loaded=model_loaded,
        version=settings.VERSION,
        timestamp=datetime.now(UTC),
    ).model_dump(mode="json")

    return JSONResponse(status_code=status_code, content=content)


@router.get(
    "/metrics",
    summary="Prometheus monitoring metrics endpoint",
)
def prometheus_metrics():
    """Expose application metrics in Prometheus exposition format."""
    return get_prometheus_metrics()
