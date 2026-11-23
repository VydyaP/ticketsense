from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "TicketSense API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database URLs
    # Defaults to async SQLite for local lightweight execution, overridden by Postgres in production/compose
    DATABASE_URL: str = "sqlite+aiosqlite:///./ticketsense.db"
    SYNC_DATABASE_URL: str = "sqlite:///./ticketsense.db"

    # CORS Configuration
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    # ML Artifacts
    MODEL_PATH: str = str(BASE_DIR / "app" / "ml" / "artifacts" / "ticket_classifier.joblib")
    METRICS_PATH: str = str(BASE_DIR / "app" / "ml" / "artifacts" / "metrics.json")

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.CORS_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
