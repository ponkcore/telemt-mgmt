"""Async database session factory (INV-EMBED).

Provides:
- ``create_session_factory(database_url)`` — creates an ``async_sessionmaker``
  for the given database URL. No module-level engine or session factory is
  created on import (INV-EMBED).
- ``get_db_session(session_factory)`` — FastAPI dependency generator that
  yields an ``AsyncSession`` from the given session factory.

All database access is async (INV-ASYNC) and via the ORM (INV-ORM).
Connection pool: ``pool_size=5``, ``max_overflow=10`` for PostgreSQL
(ADR-006). SQLite (used for tests) uses StaticPool.

Environment:
    The caller is responsible for obtaining the ``DATABASE_URL`` (e.g. from
    an env var) and passing it to ``create_session_factory()``. This module
    does NOT read env vars — that would be a module-level side effect
    (INV-EMBED).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine


def create_session_factory(
    database_url: str,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory for the given database URL.

    This is the sole entry point for obtaining a session factory. It must
    be called explicitly (e.g. in ``setup_bot()`` or ``create_app()``)
    rather than at module import time (INV-EMBED).

    Args:
        database_url: SQLAlchemy async URL (e.g.
            ``postgresql+asyncpg://user:pass@host:5432/db`` or
            ``sqlite+aiosqlite:///:memory:``).

    Returns:
        An ``async_sessionmaker[AsyncSession]`` bound to a new engine.
    """
    engine_kwargs: dict[str, Any] = {"echo": False}

    # SQLite (used for tests) does not support pool_size / max_overflow
    # because it uses StaticPool. For PostgreSQL (asyncpg) and other pooled
    # dialects we apply ADR-006's pool_size=5, max_overflow=10.
    is_sqlite = database_url.startswith("sqlite")
    if not is_sqlite:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

    engine: AsyncEngine = create_async_engine(database_url, **engine_kwargs)
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-compatible async dependency that yields a database session.

    Usage in FastAPI::

        from functools import partial
        from telemt_proxy.database import create_session_factory, get_db_session

        factory = create_session_factory(database_url)
        # Bind the factory into the dependency:
        get_session = partial(get_db_session, factory)

        @router.get("/items")
        async def list_items(session: AsyncSession = Depends(get_session)):
            ...

    Args:
        session_factory: The ``async_sessionmaker`` to obtain sessions from.

    Yields:
        An ``AsyncSession``. Rolls back on exception before closing.
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Backward-compat: allow ``os.environ.get("DATABASE_URL")`` lookups from
# callers that need the URL (e.g. api/deps.py reads it and passes it to
# create_session_factory). This does NOT create an engine.
DEFAULT_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"


def get_database_url() -> str:
    """Return the database URL from the ``DATABASE_URL`` env var.

    This is a convenience helper for callers that want the default URL
    without reading the env var directly. It does NOT create an engine
    (INV-EMBED).
    """
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
