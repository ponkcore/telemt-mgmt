"""Shared pytest fixtures for telemt-mgmt test suite."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Set test env vars BEFORE importing api modules (they read env at import).
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TELEMT_API_URL", "http://telemt.test:9091")
os.environ.setdefault("TELEMT_AUTH_HEADER", "Bearer test-token")
os.environ.setdefault("TELEMT_PROXY_SERVER", "proxy.example.com")
os.environ.setdefault("TELEMT_PROXY_PORT", "443")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

# Now import after env vars are set.
from api.auth import create_access_token, get_password_hash, rate_limiter  # noqa: E402
from api.deps import get_db_session, get_telemt_client  # noqa: E402
from api.main import create_app  # noqa: E402
from telemt_proxy.client import TelemtClient  # noqa: E402
from telemt_proxy.models import AdminUser, Base  # noqa: E402

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from httpx import AsyncClient


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Create an in-memory async SQLite engine for testing."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _enable_fk(dbapi_conn: sqlite3.Connection, connection_record: object) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session_factory(
    db_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Async session factory bound to the test engine."""
    return async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield an async session for each test."""
    async with db_session_factory() as session:
        yield session


@pytest.fixture
async def admin_user(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[str]:
    """Create a test admin user and return the username."""
    async with db_session_factory() as session:
        password_hash = get_password_hash("testpass123")
        admin = AdminUser(
            username="testadmin",
            password_hash=password_hash,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
    yield "testadmin"  # noqa: PT022


@pytest.fixture
def auth_token(admin_user: str) -> str:
    """Create a JWT access token for the test admin user."""
    return create_access_token(admin_user)


@pytest.fixture
def app(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[FastAPI]:
    """Create a FastAPI test app with overridden dependencies."""
    test_app = create_app()

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with db_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    test_app.dependency_overrides[get_db_session] = _override_db

    def _override_telemt_client() -> TelemtClient:
        return TelemtClient(
            base_url="http://telemt.test:9091",
            auth_header="Bearer test-token",
        )

    test_app.dependency_overrides[get_telemt_client] = _override_telemt_client
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Create an async HTTP test client for the FastAPI app."""

    from httpx import ASGITransport
    from httpx import AsyncClient as HttpxAsyncClient

    transport = ASGITransport(app=app)
    async with HttpxAsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> AsyncIterator[None]:
    """Reset the rate limiter before and after each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Return Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}
