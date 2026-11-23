#!/bin/sh
# Container start command: migrate the database, then start the API.
# `set -e` means a failed migration stops the container (and the deploy)
# instead of starting an API against an out-of-date schema.
set -e

echo "[entrypoint] Applying database migrations..."
alembic upgrade head

echo "[entrypoint] Starting API on port ${PORT:-8000}..."
# One worker: the free hosting tier has 512 MB RAM, and Prometheus counters
# live in process memory, so a single process keeps /metrics accurate.
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" --proxy-headers --forwarded-allow-ips="*"
