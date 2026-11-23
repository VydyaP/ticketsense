from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import settings

# pool_pre_ping: serverless Postgres (Neon) closes idle connections, so check a
# pooled connection is alive before handing it to a request.
async_engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models. The schema itself is managed by Alembic."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one database session per request, always closed afterwards."""
    async with AsyncSessionLocal() as session:
        yield session
