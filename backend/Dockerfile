# Multi-stage Dockerfile for TicketSense Backend API
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy backend codebase, migrations, alembic config, and ML artifacts
COPY backend /app/backend
COPY alembic.ini /app/alembic.ini
COPY ml/metrics.json /app/backend/app/ml/artifacts/metrics.json

# Ensure entrypoint script is executable
RUN chmod +x /app/backend/entrypoint.sh

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/backend/entrypoint.sh"]
