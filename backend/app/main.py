from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.health import router as health_router
from backend.app.api.predict import router as predict_router
from backend.app.api.stats import router as stats_router
from backend.app.api.tickets import router as tickets_router
from backend.app.core.config import settings
from backend.app.core.database import async_engine
from backend.app.core.logging import RequestLoggingMiddleware, logger
from backend.app.core.metrics import PrometheusMetricsMiddleware
from backend.app.ml.model import ModelNotLoadedError, model_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hook. The schema is created by Alembic (see entrypoint.sh), not here."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    if not model_service.is_loaded:
        logger.error("Model not loaded: prediction endpoints will return 503 until fixed")
    yield
    await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="IT help-desk tickets with machine-learning triage (category + priority).",
    lifespan=lifespan,
)

# Middleware runs outermost-last-added: CORS -> metrics -> request logging -> routes.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.exception_handler(ModelNotLoadedError)
async def model_not_loaded_handler(request: Request, exc: ModelNotLoadedError) -> JSONResponse:
    """Fail loudly with 503 rather than returning a made-up prediction."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(health_router)
app.include_router(tickets_router)
app.include_router(predict_router)
app.include_router(stats_router)


@app.get("/", tags=["Root"], summary="API index")
async def root() -> dict[str, str]:
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }
