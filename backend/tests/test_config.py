"""Unit tests for DATABASE_URL handling (no database needed)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings

NEON = "postgresql://user:pw@ep-x-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


def test_neon_url_is_translated_for_both_drivers():
    s = Settings(DATABASE_URL=NEON)
    assert s.async_database_url == (
        "postgresql+asyncpg://user:pw@ep-x-pooler.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
    )
    assert s.sync_database_url.startswith("postgresql+psycopg2://user:pw@")
    assert "sslmode=require" in s.sync_database_url


def test_quotes_and_whitespace_from_copy_paste_are_tolerated():
    assert Settings(DATABASE_URL=f"  '{NEON}'\n").DATABASE_URL == NEON


@pytest.mark.parametrize("bad", ["", "ep-x.neon.tech/neondb", "mysql://u:p@h/db"])
def test_bad_url_gives_readable_error_without_password(bad: str):
    with pytest.raises(ValidationError) as err:
        Settings(DATABASE_URL=bad)
    assert "DATABASE_URL must look like" in str(err.value)


def test_error_never_contains_the_password():
    with pytest.raises(ValidationError) as err:
        Settings(DATABASE_URL="neondb_owner:SuperSecret123@ep-x.neon.tech/neondb")
    assert "SuperSecret123" not in str(err.value)
