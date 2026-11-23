from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.api.predict import router as predict_router
from backend.app.api.stats import router as stats_router
from backend.app.api.tickets import router as tickets_router
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.logging import RequestLoggingMiddleware, logger
from backend.app.core.metrics import PrometheusMetricsMiddleware
from backend.app.ml.model import model_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hook: verifies database and ML artifacts on startup."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")

    # Initialize DB tables if SQLite is used locally
    if "sqlite" in settings.DATABASE_URL:
        logger.info("Initializing SQLite tables...")
        await init_db()

    if not model_service.is_loaded:
        logger.warning(
            "ML Model bundle was not loaded on startup. Predictions may use fallback heuristics."
        )
    else:
        logger.info("ML Model bundle loaded and ready for inference.")

    yield
    logger.info("Shutting down TicketSense API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="IT Support Ticket Triage API with Machine Learning Categorization and Prioritization",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Middleware: Request Logging and Prometheus Metrics
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)

# Middleware: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(health_router)
app.include_router(tickets_router)
app.include_router(predict_router)
app.include_router(stats_router)


@app.get("/", tags=["Root"])
async def root():
    """API root providing metadata and links to docs."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }
