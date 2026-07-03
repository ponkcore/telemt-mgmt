"""User management endpoints (C3).

Per ARCH-001@0.1.1 §3 C3:
  - GET /api/users — list all proxy users (telemt data + local labels), paginated.
  - POST /api/users/{username}/disable — disable user in telemt.
  - POST /api/users/{username}/enable — enable user in telemt.

All endpoints require valid JWT (AC2) except /api/health and /api/auth/login.
502 returned when telemt API is unreachable (AC7).
Telemt stats merged into user list (AC3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from api.deps import get_current_user, get_db_session, get_telemt_client
from api.schemas import UserActionResponse, UserListResponse, UserResponse
from telemt_proxy.exceptions import TelemtConnectionError, TelemtNotFoundError
from telemt_proxy.models import ProxyUser

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from telemt_proxy.client import TelemtClient

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _current_user: str = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    telemt_client: TelemtClient = Depends(get_telemt_client),  # noqa: B008
) -> UserListResponse:
    """List all proxy users with telemt stats merged.

    Fetches local proxy_users from DB (paginated), then merges telemt
    connection/IP stats for each user.

    Args:
        page: Page number (1-indexed).
        per_page: Items per page (1-100, default 20).
        _current_user: The authenticated admin username (JWT required).
        db: The async database session.
        telemt_client: The telemt API client.

    Returns:
        UserListResponse with items, total, page, per_page.

    Raises:
        HTTPException: 502 if telemt API is unreachable (AC7).
    """
    # Count total local proxy users.
    count_result = await db.execute(select(func.count()).select_from(ProxyUser))
    total: int = count_result.scalar_one()

    # Fetch paginated local proxy users.
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ProxyUser)
        .order_by(ProxyUser.id)
        .offset(offset)
        .limit(per_page)
    )
    local_users: list[ProxyUser] = list(result.scalars().all())

    # Fetch telemt connection stats for merging (AC3).
    connections_by_user: dict[str, int] = {}
    ips_by_user: dict[str, int] = {}
    try:
        async with telemt_client as client:
            conn_summary = await client.get_connections_summary()
            for conn in conn_summary:
                if conn.connections is not None:
                    connections_by_user[conn.username] = conn.connections
            active_ips = await client.get_active_ips()
            for ip_info in active_ips:
                if ip_info.ip_count is not None:
                    ips_by_user[ip_info.username] = ip_info.ip_count
    except TelemtConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telemt API unreachable: {exc}",
        ) from exc

    # Merge telemt data with local data.
    items: list[UserResponse] = []
    for lu in local_users:
        items.append(
            UserResponse(
                name=lu.telemt_username,
                is_disabled=not lu.is_active,
                source=lu.source,
                created_at=lu.created_at,
                is_active=lu.is_active,
                ip_count=ips_by_user.get(lu.telemt_username),
                connections=connections_by_user.get(lu.telemt_username),
            )
        )

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/users/{username}/disable", response_model=UserActionResponse)
async def disable_user(
    username: str,
    _current_user: str = Depends(get_current_user),  # noqa: B008
    telemt_client: TelemtClient = Depends(get_telemt_client),  # noqa: B008
) -> UserActionResponse:
    """Disable a telemt proxy user.

    Args:
        username: The telemt username to disable.
        _current_user: The authenticated admin username (JWT required).
        telemt_client: The telemt API client.

    Returns:
        UserActionResponse with username and is_disabled=True.

    Raises:
        HTTPException: 502 if telemt API is unreachable (AC7).
        HTTPException: 404 if user not found in telemt.
    """
    try:
        async with telemt_client as client:
            await client.disable_user(username)
    except TelemtConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telemt API unreachable: {exc}",
        ) from exc
    except TelemtNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {username}",
        ) from exc

    return UserActionResponse(username=username, is_disabled=True)


@router.post("/users/{username}/enable", response_model=UserActionResponse)
async def enable_user(
    username: str,
    _current_user: str = Depends(get_current_user),  # noqa: B008
    telemt_client: TelemtClient = Depends(get_telemt_client),  # noqa: B008
) -> UserActionResponse:
    """Enable a telemt proxy user.

    Args:
        username: The telemt username to enable.
        _current_user: The authenticated admin username (JWT required).
        telemt_client: The telemt API client.

    Returns:
        UserActionResponse with username and is_disabled=False.

    Raises:
        HTTPException: 502 if telemt API is unreachable (AC7).
        HTTPException: 404 if user not found in telemt.
    """
    try:
        async with telemt_client as client:
            await client.enable_user(username)
    except TelemtConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telemt API unreachable: {exc}",
        ) from exc
    except TelemtNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {username}",
        ) from exc

    return UserActionResponse(username=username, is_disabled=False)
