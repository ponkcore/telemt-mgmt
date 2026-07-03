"""Tests for the auth API — login, token validation, rate limiting, 401 on invalid.

Covers:
  - AC1: POST /api/auth/login returns JWT on valid creds, 401 on invalid.
  - AC2: Endpoints require JWT (tests that protected endpoints return 401 without token).
  - AC6: Rate limiter returns 429 after 5 failed login attempts from same IP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from api.auth import create_access_token, get_password_hash, rate_limiter

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

BASE_URL = "http://telemt.test:9091"


# ── AC1: Login returns JWT on valid creds, 401 on invalid ──────────────────


@pytest.mark.asyncio
async def test_login_valid_credentials(
    client: AsyncClient,
    admin_user: str,
) -> None:
    """POST /api/auth/login with valid creds returns 200 + JWT token (AC1)."""
    response = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_invalid_password(
    client: AsyncClient,
    admin_user: str,
) -> None:
    """POST /api/auth/login with wrong password returns 401 (AC1)."""
    response = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """POST /api/auth/login with nonexistent user returns 401 (AC1)."""
    response = await client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_empty_body(client: AsyncClient) -> None:
    """POST /api/auth/login with empty body returns 422."""
    response = await client.post(
        "/api/auth/login",
        json={"username": "", "password": ""},
    )
    assert response.status_code == 422


# ── AC2: Protected endpoints require JWT ──────────────────────────────────


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient) -> None:
    """GET /api/users without token returns 401/403 (AC2)."""
    response = await client.get("/api/users")
    assert response.status_code == 401 or response.status_code == 403


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(client: AsyncClient) -> None:
    """GET /api/users with invalid token returns 401 (AC2)."""
    response = await client.get(
        "/api/users",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_no_auth_required(client: AsyncClient) -> None:
    """GET /api/health does not require JWT (AC2)."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/users with valid token does not return 401 (AC2).

    This tests that the JWT validation passes. The response may be 502
    if telemt is unreachable, but it should not be 401.
    """
    with respx.mock:
        respx.get(f"{BASE_URL}/v1/stats/summary").mock(
            return_value=httpx.Response(
                200,
                json={"active_users": 0, "total_connections": 0, "total_traffic": 0},
            )
        )
        respx.get(f"{BASE_URL}/v1/runtime/connections/summary").mock(
            return_value=httpx.Response(200, json=[])
        )
        respx.get(f"{BASE_URL}/v1/stats/users/active-ips").mock(
            return_value=httpx.Response(200, json=[])
        )
        response = await client.get("/api/users", headers=auth_headers)
    assert response.status_code != 401


# ── AC6: Rate limiting — 429 after 5 failed attempts ──────────────────────


@pytest.mark.asyncio
async def test_rate_limit_after_5_failed_attempts(
    client: AsyncClient,
    admin_user: str,
) -> None:
    """Rate limiter returns 429 after 5 failed login attempts (AC6)."""
    rate_limiter.reset()

    # Make 5 failed attempts (should all return 401).
    for i in range(5):
        response = await client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": "wrongpass"},
        )
        assert response.status_code == 401, f"Attempt {i + 1} should be 401"

    # 6th attempt should be rate-limited (429).
    response = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "wrongpass"},
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_does_not_block_valid_login(
    client: AsyncClient,
    admin_user: str,
) -> None:
    """Valid logins should not be rate-limited even after some failed attempts."""
    rate_limiter.reset()

    # Make 3 failed attempts (below the threshold).
    for _ in range(3):
        await client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": "wrongpass"},
        )

    # A valid login should still work.
    response = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_rate_limit_retry_after_header(
    client: AsyncClient,
    admin_user: str,
) -> None:
    """429 response includes a Retry-After header (AC6)."""
    rate_limiter.reset()

    # Exhaust the rate limit.
    for _ in range(5):
        await client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": "wrongpass"},
        )

    response = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "wrongpass"},
    )
    assert response.status_code == 429
    retry_after = response.headers.get("Retry-After")
    assert retry_after is not None
    assert int(retry_after) >= 1


# ── Token validation tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expired_token_rejected(
    client: AsyncClient,
    admin_user: str,
) -> None:
    """An expired JWT is rejected with 401."""
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    expired_token = jwt.encode(
        {
            "sub": "testadmin",
            "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
        },
        "test-secret-key-for-testing",
        algorithm="HS256",
    )
    response = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_with_wrong_secret_rejected(
    client: AsyncClient,
    admin_user: str,
) -> None:
    """A JWT signed with the wrong secret is rejected with 401."""
    from jose import jwt

    bad_token = jwt.encode(
        {"sub": "testadmin", "exp": 9999999999},
        "wrong-secret",
        algorithm="HS256",
    )
    response = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_for_inactive_admin_rejected(
    client: AsyncClient,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A JWT for an inactive admin user is rejected with 401."""
    from sqlalchemy import update

    from telemt_proxy.models import AdminUser

    # Create the admin user first.
    async with db_session_factory() as session:
        password_hash = get_password_hash("testpass123")
        admin = AdminUser(
            username="testadmin", password_hash=password_hash, is_active=True
        )
        session.add(admin)
        await session.commit()

    # Create token while admin is active.
    token = create_access_token("testadmin")

    # Deactivate the admin.
    async with db_session_factory() as session:
        await session.execute(
            update(AdminUser)
            .where(AdminUser.username == "testadmin")
            .values(is_active=False)
        )
        await session.commit()

    # Token should now be rejected.
    response = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
