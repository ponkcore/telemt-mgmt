"""Tests for the links API — GET /api/links, POST /api/links, DELETE /api/links/{id}.

Covers:
  - AC2: Endpoints require JWT.
  - AC4: POST /api/links creates telemt user + DB record, returns proxy link.
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

USER_JSON = {"name": "a1b2c3d4e5f6a7b8", "secret": "secret123abc", "is_disabled": False}


# ── AC4: POST /api/links creates telemt user + DB record, returns proxy link ─


@pytest.mark.asyncio
async def test_create_link(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """POST /api/links creates telemt user + DB record, returns proxy link (AC4)."""
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users").mock(
            return_value=httpx.Response(200, json=USER_JSON)
        )
        response = await client.post(
            "/api/links",
            json={"label": "forum-4pda"},
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["label"] == "forum-4pda"
    assert "proxy_link" in data
    assert data["proxy_link"].startswith("tg://proxy?")
    assert "proxy.example.com" in data["proxy_link"]
    assert data["is_active"] is True

    # Verify DB record was created.
    async with db_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(LabelledLink).where(LabelledLink.label == "forum-4pda")
        )
        link = result.scalar_one_or_none()
    assert link is not None
    assert link.proxy_link == data["proxy_link"]


@pytest.mark.asyncio
async def test_create_link_duplicate_label(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """POST /api/links with duplicate label returns 409."""
    # Create a link first.
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users").mock(
            return_value=httpx.Response(200, json=USER_JSON)
        )
        await client.post(
            "/api/links",
            json={"label": "duplicate"},
            headers=auth_headers,
        )

    # Try to create the same label again.
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users").mock(
            return_value=httpx.Response(200, json=USER_JSON)
        )
        response = await client.post(
            "/api/links",
            json={"label": "duplicate"},
            headers=auth_headers,
        )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_link_telemt_unreachable(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /api/links returns 502 when telemt is unreachable (AC7)."""
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.post(
            "/api/links",
            json={"label": "test-label"},
            headers=auth_headers,
        )
    assert response.status_code == 502


# ── GET /api/links ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_links_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/links with no links returns empty list."""
    response = await client.get("/api/links", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_links_with_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """GET /api/links returns existing links."""
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
            label="test-label",
            telemt_username="a1b2c3d4e5f6a7b8",
            proxy_link="tg://proxy?server=proxy.example.com&port=443&secret=abc",
            is_active=True,
        )
        session.add(link)
        await session.commit()

    response = await client.get("/api/links", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["label"] == "test-label"


# ── DELETE /api/links/{id} ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_link(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """DELETE /api/links/{id} deletes the link and disables telemt user."""
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
            label="delete-me",
            telemt_username="a1b2c3d4e5f6a7b8",
            proxy_link="tg://proxy?server=proxy.example.com&port=443&secret=abc",
            is_active=True,
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)
        link_id = link.id

    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users/a1b2c3d4e5f6a7b8/disable").mock(
            return_value=httpx.Response(200, json={})
        )
        response = await client.delete(
            f"/api/links/{link_id}", headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == link_id
    assert data["deleted"] is True

    # Verify the link is deleted from DB.
    async with db_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(LabelledLink).where(LabelledLink.id == link_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_link_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """DELETE /api/links/{id} with nonexistent ID returns 404."""
    response = await client.delete("/api/links/9999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_link_telemt_unreachable(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """DELETE /api/links/{id} returns 502 when telemt is unreachable (AC7)."""
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
            label="telemt-down",
            telemt_username="a1b2c3d4e5f6a7b8",
            proxy_link="tg://proxy?server=proxy.example.com&port=443&secret=abc",
            is_active=True,
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)
        link_id = link.id

    with respx.mock:
        respx.post(f"{BASE_URL}/v1/users/a1b2c3d4e5f6a7b8/disable").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.delete(
            f"/api/links/{link_id}", headers=auth_headers
        )

    assert response.status_code == 502


# ── AC2: Auth required ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_links_no_auth(client: AsyncClient) -> None:
    """GET /api/links without auth returns 401 (AC2)."""
    response = await client.get("/api/links")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_link_no_auth(client: AsyncClient) -> None:
    """POST /api/links without auth returns 401 (AC2)."""
    response = await client.post("/api/links", json={"label": "test"})
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_link_no_auth(client: AsyncClient) -> None:
    """DELETE /api/links/{id} without auth returns 401 (AC2)."""
    response = await client.delete("/api/links/1")
    assert response.status_code in (401, 403)
