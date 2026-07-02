"""Async database engine, session factory, and FastAPI dependency.

Provides:
- ``engine`` — module-level ``AsyncEngine`` created from ``DATABASE_URL``.
- ``async_session_factory`` — ``async_sessionmaker`` for creating sessions.
- ``get_db_session()`` — async generator usable as a FastAPI ``Depends()``.

All database access is async (INV-ASYNC) and via the ORM (INV-ORM).
Connection pool: ``pool_size=5``, ``max_overflow=10`` (ADR-006).

Environment:
    ``DATABASE_URL`` — SQLAlchemy async URL (e.g.
    ``postgresql+asyncpg://user:pass@host:5432/db``).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

# SQLite (used for tests) does not support pool_size / max_overflow because
# it uses StaticPool. For PostgreSQL (asyncpg) and other pooled dialects we
# apply ADR-006's pool_size=5, max_overflow=10 configuration.
_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict[str, Any] = {"echo": False}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    **_engine_kwargs,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-compatible async dependency that yields a database session.

    Usage in FastAPI::

        @router.get("/items")
        async def list_items(
            session: AsyncSession = Depends(get_db_session)
        ):
            ...

    Yields:
        An ``AsyncSession`` and rolls back on exception before closing.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
