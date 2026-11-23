#!/bin/sh
set -e

echo "[TicketSense] Running database migrations..."
alembic upgrade head || {
    echo "[TicketSense] Migration command failed or already applied. Proceeding..."
}

echo "[TicketSense] Starting FastAPI server..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WORKERS:-2}"
