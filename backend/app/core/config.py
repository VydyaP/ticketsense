from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend
ARTIFACT_DIR = BASE_DIR / "app" / "ml" / "artifacts"


def _with_driver(url: str, driver: str) -> str:
    """Return `url` with its scheme set to postgresql+<driver>.

    Hosting providers (Neon, Render) hand out plain `postgresql://` or
    `postgres://` URLs. The app needs two drivers: asyncpg for the API and
    psycopg2 for Alembic migrations, so we derive both from one setting.
    """
    scheme, rest = url.split("://", 1)
    if not scheme.startswith("postgres"):
        raise ValueError(f"DATABASE_URL must be a PostgreSQL URL, got scheme '{scheme}'")
    return f"postgresql+{driver}://{rest}"


def _asyncpg_query(url: str) -> str:
    """Translate libpq query params that asyncpg does not understand.

    Neon URLs end with `?sslmode=require&channel_binding=require`; asyncpg
    expects `ssl=require` and rejects `channel_binding`.
    """
    parts = urlsplit(url)
    params = []
    for key, value in parse_qsl(parts.query):
        if key == "sslmode":
            params.append(("ssl", value))
        elif key != "channel_binding":
            params.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(params)))


class Settings(BaseSettings):
    """Application configuration, read from environment variables (or a root .env file)."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "TicketSense API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # One plain PostgreSQL URL, e.g. postgresql://user:pass@host:5432/db?sslmode=require
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ticketsense"

    # Comma-separated list of allowed browser origins (the frontend URL in production).
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    MODEL_PATH: str = str(ARTIFACT_DIR / "ticket_classifier.joblib")
    METRICS_PATH: str = str(ARTIFACT_DIR / "metrics.json")

    @property
    def async_database_url(self) -> str:
        return _asyncpg_query(_with_driver(self.DATABASE_URL, "asyncpg"))

    @property
    def sync_database_url(self) -> str:
        return _with_driver(self.DATABASE_URL, "psycopg2")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
