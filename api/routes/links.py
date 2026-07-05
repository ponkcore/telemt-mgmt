"""Labelled link CRUD endpoints (C3).

Per ARCH-001@0.1.1 §3 C3:
  - GET /api/links — list all labelled links.
  - POST /api/links — create labelled link {label}, creates telemt user,
    stores in DB, returns proxy link.
  - DELETE /api/links/{id} — delete labelled link (disables telemt user).

All endpoints require valid JWT (AC2).
502 returned when telemt API is unreachable (AC7).
POST creates telemt user + DB record, returns proxy link (AC4).
"""

from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.deps import get_current_user, get_db_session, get_telemt_client
from api.schemas import (
    LinkCreate,
    LinkDeleteResponse,
    LinkListResponse,
    LinkResponse,
)
from telemt_proxy.exceptions import TelemtConnectionError
from telemt_proxy.link import build_proxy_link
from telemt_proxy.models import LabelledLink, ProxyUser

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from telemt_proxy.client import TelemtClient

router = APIRouter(prefix="/api", tags=["links"])

# Proxy server config for building links (INV-DOMAIN: domain, not IP).
TELEMT_PROXY_SERVER: str = os.environ.get("TELEMT_PROXY_SERVER", "proxy.example.com")
TELEMT_PROXY_PORT: int = int(os.environ.get("TELEMT_PROXY_PORT", "443"))


@router.get("/links", response_model=LinkListResponse)
async def list_links(
    _current_user: str = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> LinkListResponse:
    """List all labelled links from the database.

    Args:
        _current_user: The authenticated admin username (JWT required).
        db: The async database session.

    Returns:
        LinkListResponse with all labelled links.
    """
    result = await db.execute(
        select(LabelledLink).order_by(LabelledLink.id)
    )
    links: list[LabelledLink] = list(result.scalars().all())
    items: list[LinkResponse] = [
        LinkResponse(
            id=link.id,
            label=link.label,
            telemt_username=link.telemt_username,
            proxy_link=link.proxy_link,
            is_active=link.is_active,
            created_at=link.created_at,
        )
        for link in links
    ]
    return LinkListResponse(items=items)


@router.post("/links", response_model=LinkResponse, status_code=201)
async def create_link(
    body: LinkCreate,
    _current_user: str = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    telemt_client: TelemtClient = Depends(get_telemt_client),  # noqa: B008
) -> LinkResponse:
    """Create a labelled link.

    Creates a telemt user via the API, stores a proxy_user + labelled_link
    in the DB, and returns the proxy link (AC4).

    The telemt username is derived from the label hash to ensure uniqueness.

    Args:
        body: The link creation request containing the label.
        _current_user: The authenticated admin username (JWT required).
        db: The async database session.
        telemt_client: The telemt API client.

    Returns:
        LinkResponse with the created link.

    Raises:
        HTTPException: 502 if telemt API is unreachable (AC7).
        HTTPException: 409 if the label already exists.
    """
    # Check if label already exists.
    existing = await db.execute(
        select(LabelledLink).where(LabelledLink.label == body.label)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Label already exists: {body.label}",
        )

    # Create a telemt user. The username is a hash of the label for uniqueness.
    telemt_username = hashlib.sha256(body.label.encode()).hexdigest()[:16]

    # NOTE: Admin-created labelled links intentionally bypass hash_telegram_id()
    # (L5 code-review finding). Admin links are not tied to a Telegram user —
    # they are operator-defined labelled links with no Telegram ID. Therefore
    # there is no telegram_id to hash with HASHING_SALT. Instead, the label
    # itself is hashed directly (SHA256) to produce both telemt_username and
    # telegram_id_hash. The salt omission is acceptable because labels are
    # operator-chosen strings, not PII. This is an intentional divergence from
    # INV-HASH, which applies only to real Telegram user IDs.

    try:
        async with telemt_client as client:
            telemt_user = await client.create_user(telemt_username)
    except TelemtConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telemt API unreachable: {exc}",
        ) from exc

    secret = telemt_user.secret or ""
    proxy_link = build_proxy_link(TELEMT_PROXY_SERVER, TELEMT_PROXY_PORT, secret)

    # Store in DB: proxy_user + labelled_link.
    proxy_user = ProxyUser(
        telemt_username=telemt_username,
        telegram_id_hash=hashlib.sha256(body.label.encode()).hexdigest(),
        source="admin_label",
        is_active=True,
    )
    db.add(proxy_user)
    try:
        await db.flush()
    except IntegrityError as exc:
        # The proxy_user may already exist (label reuse with same hash).
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Telemt user already exists: {telemt_username}",
        ) from exc

    labelled_link = LabelledLink(
        label=body.label,
        telemt_username=telemt_username,
        proxy_link=proxy_link,
        is_active=True,
    )
    db.add(labelled_link)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Label already exists: {body.label}",
        ) from exc

    return LinkResponse(
        id=labelled_link.id,
        label=labelled_link.label,
        telemt_username=labelled_link.telemt_username,
        proxy_link=labelled_link.proxy_link,
        is_active=labelled_link.is_active,
        created_at=labelled_link.created_at,
    )


@router.delete("/links/{link_id}", response_model=LinkDeleteResponse)
async def delete_link(
    link_id: int,
    _current_user: str = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    telemt_client: TelemtClient = Depends(get_telemt_client),  # noqa: B008
) -> LinkDeleteResponse:
    """Delete a labelled link (disables the telemt user).

    Args:
        link_id: The ID of the labelled link to delete.
        _current_user: The authenticated admin username (JWT required).
        db: The async database session.
        telemt_client: The telemt API client.

    Returns:
        LinkDeleteResponse with id and deleted=True.

    Raises:
        HTTPException: 404 if the link is not found.
        HTTPException: 502 if telemt API is unreachable (AC7).
    """
    result = await db.execute(
        select(LabelledLink).where(LabelledLink.id == link_id)
    )
    link: LabelledLink | None = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link not found: {link_id}",
        )

    # Disable the telemt user (best-effort).
    try:
        async with telemt_client as client:
            await client.disable_user(link.telemt_username)
    except TelemtConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telemt API unreachable: {exc}",
        ) from exc

    # Mark link as inactive and delete from DB.
    link.is_active = False
    await db.delete(link)
    await db.commit()

    return LinkDeleteResponse(id=link_id, deleted=True)
