# TicketSense API image. Build from the repo root:
#   docker build -f backend/Dockerfile -t ticketsense-backend .
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# curl is only used by the HEALTHCHECK below. The DB drivers ship as wheels, so no compiler is needed.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so Docker caches this layer when only code changes.
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY alembic.ini ./alembic.ini
COPY backend ./backend
RUN rm -rf backend/tests && chmod +x backend/entrypoint.sh

# Run as an unprivileged user.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/health" || exit 1

CMD ["/app/backend/entrypoint.sh"]
