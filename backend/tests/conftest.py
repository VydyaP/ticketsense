"""Shared test fixtures.

API tests run against a REAL PostgreSQL database (a Docker container locally,
a service container in CI), with the schema created by our Alembic migrations.
That way the tests also prove the migrations work, and Postgres-specific
behaviour (JSON columns, ILIKE, timezones) is exercised for real.

Point TEST_DATABASE_URL at a throwaway database: tables are truncated between tests.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Iterator

# Must be set BEFORE importing the app, because settings are read at import time.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ticketsense_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from backend.app.core.config import settings  # noqa: E402
from backend.app.core.database import async_engine  # noqa: E402
from backend.app.main import app  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Build the schema once per test run by running every migration down and up."""
    config = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(REPO_ROOT, "backend", "migrations"))
    command.downgrade(config, "base")  # start clean even if a previous run crashed
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    """Empty the tickets table before each test so tests don't depend on each other."""
    engine = create_engine(settings.sync_database_url)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE tickets RESTART IDENTITY"))
    engine.dispose()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client that calls the FastAPI app in-process (no server needed)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    # pytest-asyncio gives each test its own event loop; pooled asyncpg
    # connections belong to the old loop, so drop them after every test.
    await async_engine.dispose()
