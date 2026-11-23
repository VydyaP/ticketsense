"""Structured JSON logging with a request ID on every line.

How the request ID reaches every log line: the middleware stores it in a
ContextVar (a per-request variable that is safe with async code), and a
logging.Filter copies it onto every LogRecord, including records emitted by
services, the ML module or libraries while that request is being handled.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_EXTRA_FIELDS = ("method", "path", "status_code", "duration_ms")


class RequestIdFilter(logging.Filter):
    """Attach the current request ID (or '-' outside a request) to each record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JSONLogFormatter(logging.Formatter):
    """Render each record as one JSON object per line (easy to search in log tools)."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            if hasattr(record, field):
                entry[field] = getattr(record, field)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging(level: str) -> logging.Logger:
    """Install one JSON handler on the root logger so every library logs the same way."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Route uvicorn's own loggers through the root handler instead of its plain-text one.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    # The middleware below already logs each request, so drop uvicorn's duplicate access log.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return logging.getLogger("ticketsense")


logger = setup_logging(settings.LOG_LEVEL)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assign a request ID, log method/path/status/latency, and return X-Request-ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Reuse an incoming X-Request-ID (e.g. from a proxy) so IDs can be traced across services.
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled error",
                extra={"method": request.method, "path": request.url.path, "status_code": 500},
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        # Health checks and Prometheus scrapes run every few seconds; only log them if they fail.
        if request.url.path not in ("/health", "/metrics") or response.status_code >= 400:
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        request_id_var.reset(token)
        return response
