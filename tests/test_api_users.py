"""Tests for the users API — GET /api/users, disable/enable.

Covers:
  - AC2: Endpoints require JWT.
  - AC3: GET /api/users returns paginated list with telemt stats merged.
  - AC7: 502 returned when telemt API is unreachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from telemt_proxy.models import ProxyUser

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

BASE_URL = "http://telemt.test:9091"

USER_NO_SECRET_JSON = {"name": "a1b2c3d4e5f6a7b8", "is_disabled": False}
CONNECTIONS_JSON = [{"username": "a1b2c3d4e5f6a7b8", "connections": 3}]
ACTIVE_IPS_JSON = [{"username": "a1b2c3d4e5f6a7b8", "ip_count": 2}]
STATS_JSON = {"active_users": 1, "total_connections": 3, "total_traffic": 1024}


def _mock_telemt_user_stats() -> None:
    """Set up respx mocks for telemt user stats endpoints."""
    respx.get(f"{BASE_URL}/v1/runtime/connections/summary").mock(
        return_value=httpx.Response(200, json=CONNECTIONS_JSON)
    )
    respx.get(f"{BASE_URL}/v1/stats/users/active-ips").mock(
        return_value=httpx.Response(200, json=ACTIVE_IPS_JSON)
    )


# ── AC3: GET /api/users paginated with telemt stats merged ─────────────────


@pytest.mark.asyncio
async def test_list_users_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/users with no users returns empty list (AC3)."""
    with respx.mock:
        _mock_telemt_user_stats()
        response = await client.get("/api/users", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20


@pytest.mark.asyncio
async def test_list_users_with_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """GET /api/users returns users with telemt stats merged (AC3)."""
    async with db_session_factory() as session:
        user = ProxyUser(
            telemt_username="a1b2c3d4e5f6a7b8",
            telegram_id_hash="a" * 64,
            source="bot",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    with respx.mock:
        _mock_telemt_user_stats()
        response = await client.get("/api/users", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["name"] == "a1b2c3d4e5f6a7b8"
    assert item["connections"] == 3
    assert item["ip_count"] == 2


@pytest.mark.asyncio
async def test_list_users_pagination(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """GET /api/users pagination works correctly (AC3)."""
    async with db_session_factory() as session:
        for i in range(25):
            user = ProxyUser(
                telemt_username=f"user{i:013d}",
                telegram_id_hash=f"h{i:063d}",
                source="bot",
                is_active=True,
            )
            session.add(user)
        await session.commit()

    with respx.mock:
        _mock_telemt_user_stats()
        # Page 1 with per_page=10
        response = await client.get(
            "/api/users?page=1&per_page=10", headers=auth_headers
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["per_page"] == 10
    assert len(data["items"]) == 10

    with respx.mock:
        _mock_telemt_user_stats()
        response = await client.get(
            "/api/users?page=3&per_page=10", headers=auth_headers
        )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 3
    assert len(data["items"]) == 5


# ── AC2: Auth required ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_users_no_auth(client: AsyncClient) -> None:
    """GET /api/users without auth returns 401 (AC2)."""
    response = await client.get("/api/users")
    assert response.status_code in (401, 403)


# ── AC7: 502 when telemt unreachable ──────────────────────────────────────


@pytest.mark.asyncio
async def test_list_users_telemt_unreachable(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """GET /api/users returns 502 when telemt is unreachable (AC7)."""
    async with db_session_factory() as session:
        user = ProxyUser(
            telemt_username="a1b2c3d4e5f6a7b8",
            telegram_id_hash="a" * 64,
            source="bot",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    with respx.mock:
        respx.get(f"{BASE_URL}/v1/runtime/connections/summary").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.get("/api/users", headers=auth_headers)

    assert response.status_code == 502


# ── Disable / Enable ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disable_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /api/users/{username}/disable disables the user."""
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users/testuser/disable").mock(
            return_value=httpx.Response(200, json={})
        )
        response = await client.post(
            "/api/users/testuser/disable", headers=auth_headers
        )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_disabled"] is True


@pytest.mark.asyncio
async def test_enable_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /api/users/{username}/enable enables the user."""
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users/testuser/enable").mock(
            return_value=httpx.Response(200, json={})
        )
        response = await client.post(
            "/api/users/testuser/enable", headers=auth_headers
        )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_disabled"] is False


@pytest.mark.asyncio
async def test_disable_user_telemt_unreachable(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /api/users/{username}/disable returns 502 when telemt unreachable (AC7)."""
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users/testuser/disable").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.post(
            "/api/users/testuser/disable", headers=auth_headers
        )
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_disable_user_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /api/users/{username}/disable returns 404 when user not found."""
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users/nonexistent/disable").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        response = await client.post(
            "/api/users/nonexistent/disable", headers=auth_headers
        )
    assert response.status_code == 404
