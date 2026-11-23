from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
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
    return f"postgresql+{driver}://{rest}"


def _check_database_url(url: str) -> str:
    """Fail at startup with a readable message (never echoing the password) if the URL is wrong."""
    url = url.strip().strip("'\"")  # tolerate stray whitespace/quotes from copy-paste
    if "://" not in url or not url.split("://", 1)[0].startswith("postgres"):
        hint = "empty" if not url else f"starts with '{url[:12]}...'"
        raise ValueError(
            "DATABASE_URL must look like postgresql://USER:PASSWORD@HOST/DB?sslmode=require "
            f"(the current value is {hint}). Paste only the URL, without 'psql' or quotes."
        )
    return url


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
        # Never echo setting values (e.g. the DB password) in validation errors / logs.
        hide_input_in_errors=True,
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

    @field_validator("DATABASE_URL")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        return _check_database_url(value)

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
