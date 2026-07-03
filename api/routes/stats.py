"""Stats endpoints (C3).

Per ARCH-001@0.1.1 §3 C3:
  - GET /api/stats — aggregate stats (active users, connections, traffic).
  - GET /api/stats/labels — per-label connection/traffic stats.

All endpoints require valid JWT (AC2).
502 returned when telemt API is unreachable (AC7).
GET /api/stats/labels returns per-label stats (AC5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from api.deps import get_current_user, get_db_session, get_telemt_client
from api.schemas import LabelStats, LabelStatsListResponse, StatsResponse
from telemt_proxy.exceptions import TelemtConnectionError
from telemt_proxy.models import LabelledLink

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from telemt_proxy.client import TelemtClient

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    _current_user: str = Depends(get_current_user),  # noqa: B008
    telemt_client: TelemtClient = Depends(get_telemt_client),  # noqa: B008
) -> StatsResponse:
    """Get aggregate telemt statistics.

    Args:
        _current_user: The authenticated admin username (JWT required).
        telemt_client: The telemt API client.

    Returns:
        StatsResponse with active_users, total_connections, total_traffic.

    Raises:
        HTTPException: 502 if telemt API is unreachable (AC7).
    """
    try:
        async with telemt_client as client:
            stats = await client.get_stats_summary()
    except TelemtConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telemt API unreachable: {exc}",
        ) from exc

    return StatsResponse(
        active_users=stats.active_users,
        total_connections=stats.total_connections,
        total_traffic=stats.total_traffic,
    )


@router.get("/stats/labels", response_model=LabelStatsListResponse)
async def get_label_stats(
    _current_user: str = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    telemt_client: TelemtClient = Depends(get_telemt_client),  # noqa: B008
) -> LabelStatsListResponse:
    """Get per-label connection/traffic stats (AC5).

    Fetches all labelled links from DB, then queries telemt for
    per-user connection and IP stats, merging them by telemt_username.

    Args:
        _current_user: The authenticated admin username (JWT required).
        db: The async database session.
        telemt_client: The telemt API client.

    Returns:
        LabelStatsListResponse with per-label stats.

    Raises:
        HTTPException: 502 if telemt API is unreachable (AC7).
    """
    # Fetch all labelled links from DB.
    result = await db.execute(
        select(LabelledLink).where(LabelledLink.is_active.is_(True))
    )
    links: list[LabelledLink] = list(result.scalars().all())

    # Fetch telemt per-user stats.
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

    # Merge stats per label.
    items: list[LabelStats] = []
    for link in links:
        items.append(
            LabelStats(
                label=link.label,
                telemt_username=link.telemt_username,
                connections=connections_by_user.get(link.telemt_username, 0),
                ip_count=ips_by_user.get(link.telemt_username, 0),
            )
        )

    return LabelStatsListResponse(items=items)
