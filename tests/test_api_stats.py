"""Tests for the stats API — GET /api/stats, GET /api/stats/labels.

Covers:
  - AC2: Endpoints require JWT.
  - AC5: GET /api/stats/labels returns per-label connection/traffic stats.
  - AC7: 502 returned when telemt API is unreachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from telemt_proxy.models import LabelledLink, ProxyUser

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

BASE_URL = "http://telemt.test:9091"

STATS_JSON = {"active_users": 5, "total_connections": 10, "total_traffic": 1024}
CONNECTIONS_JSON = [{"username": "a1b2c3d4e5f6a7b8", "connections": 3}]
ACTIVE_IPS_JSON = [{"username": "a1b2c3d4e5f6a7b8", "ip_count": 2}]


def _mock_telemt_stats() -> None:
    """Set up respx mocks for telemt stats endpoints."""
    respx.get(f"{BASE_URL}/v1/stats/summary").mock(
        return_value=httpx.Response(200, json=STATS_JSON)
    )
    respx.get(f"{BASE_URL}/v1/runtime/connections/summary").mock(
        return_value=httpx.Response(200, json=CONNECTIONS_JSON)
    )
    respx.get(f"{BASE_URL}/v1/stats/users/active-ips").mock(
        return_value=httpx.Response(200, json=ACTIVE_IPS_JSON)
    )


# ── GET /api/stats ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_stats(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/stats returns aggregate telemt stats."""
    with respx.mock:
        _mock_telemt_stats()
        response = await client.get("/api/stats", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["active_users"] == 5
    assert data["total_connections"] == 10
    assert data["total_traffic"] == 1024


@pytest.mark.asyncio
async def test_get_stats_telemt_unreachable(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/stats returns 502 when telemt is unreachable (AC7)."""
    with respx.mock:
        respx.get(f"{BASE_URL}/v1/stats/summary").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.get("/api/stats", headers=auth_headers)

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_get_stats_no_auth(client: AsyncClient) -> None:
    """GET /api/stats without auth returns 401 (AC2)."""
    response = await client.get("/api/stats")
    assert response.status_code in (401, 403)


# ── AC5: GET /api/stats/labels — per-label stats ─────────────────────────


@pytest.mark.asyncio
async def test_get_label_stats_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/stats/labels with no links returns empty list (AC5)."""
    with respx.mock:
        _mock_telemt_stats()
        response = await client.get("/api/stats/labels", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_label_stats_with_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """GET /api/stats/labels returns per-label connection/traffic stats (AC5)."""
    async with db_session_factory() as session:
        proxy = ProxyUser(
            telemt_username="a1b2c3d4e5f6a7b8",
            telegram_id_hash="a" * 64,
            source="admin_label",
            is_active=True,
        )
        session.add(proxy)
        await session.flush()

        link = LabelledLink(
            label="forum-4pda",
            telemt_username="a1b2c3d4e5f6a7b8",
            proxy_link="tg://proxy?server=proxy.example.com&port=443&secret=abc",
            is_active=True,
        )
        session.add(link)
        await session.commit()

    with respx.mock:
        _mock_telemt_stats()
        response = await client.get("/api/stats/labels", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["label"] == "forum-4pda"
    assert item["telemt_username"] == "a1b2c3d4e5f6a7b8"
    assert item["connections"] == 3
    assert item["ip_count"] == 2


@pytest.mark.asyncio
async def test_get_label_stats_telemt_unreachable(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """GET /api/stats/labels returns 502 when telemt is unreachable (AC7)."""
    async with db_session_factory() as session:
        proxy = ProxyUser(
            telemt_username="a1b2c3d4e5f6a7b8",
            telegram_id_hash="a" * 64,
            source="admin_label",
            is_active=True,
        )
        session.add(proxy)
        await session.flush()

        link = LabelledLink(
            label="forum-4pda",
            telemt_username="a1b2c3d4e5f6a7b8",
            proxy_link="tg://proxy?server=proxy.example.com&port=443&secret=abc",
            is_active=True,
        )
        session.add(link)
        await session.commit()

    with respx.mock:
        respx.get(f"{BASE_URL}/v1/runtime/connections/summary").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.get("/api/stats/labels", headers=auth_headers)

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_get_label_stats_no_auth(client: AsyncClient) -> None:
    """GET /api/stats/labels without auth returns 401 (AC2)."""
    response = await client.get("/api/stats/labels")
    assert response.status_code in (401, 403)
