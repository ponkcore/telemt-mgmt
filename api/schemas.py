"""Pydantic v2 request/response models for the admin API (C3).

These models define the JSON contract for every endpoint in the admin API.
Per ARCH-001@0.1.1 §3 C3:
  - POST /api/auth/login — accepts {username, password}, returns {access_token, token_type}
  - GET /api/users — list proxy users with telemt stats merged
  - POST /api/links — create labelled link {label}
  - GET /api/stats, GET /api/stats/labels — aggregate and per-label stats

All models use Pydantic v2 with strict typing for mypy --strict compliance.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel, Field

# -- Auth models ---------------------------------------------------------------


class LoginRequest(BaseModel):
    """Request body for POST /api/auth/login."""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)
class TokenResponse(BaseModel):
    """Response for POST /api/auth/login on success."""

    access_token: str
    token_type: str = "bearer"
# -- User models ---------------------------------------------------------------
class UserResponse(BaseModel):
    """A proxy user with telemt data + local metadata merged.

    Fields from telemt: name, is_disabled.
    Fields from local DB: source, created_at, is_active (local mirror).
    Optional stats from telemt: ip_count, connections.
    """

    name: str
    is_disabled: bool = False
    source: str = "bot"
    created_at: datetime | None = None
    is_active: bool = True
    ip_count: int | None = None
    connections: int | None = None
class UserListResponse(BaseModel):
    """Paginated list of proxy users (GET /api/users)."""

    items: list[UserResponse]
    total: int
    page: int
    per_page: int
class UserActionResponse(BaseModel):
    """Response for disable/enable user actions."""

    username: str
    is_disabled: bool
# -- Link models ---------------------------------------------------------------
class LinkCreate(BaseModel):
    """Request body for POST /api/links."""

    label: str = Field(..., min_length=1, max_length=128)
class LinkResponse(BaseModel):
    """A labelled link (GET /api/links, POST /api/links response)."""

    id: int
    label: str
    telemt_username: str
    proxy_link: str
    is_active: bool
    created_at: datetime | None = None
class LinkListResponse(BaseModel):
    """List of labelled links (GET /api/links)."""

    items: list[LinkResponse]
class LinkDeleteResponse(BaseModel):
    """Response for DELETE /api/links/{id}."""

    id: int
    deleted: bool
# -- Stats models --------------------------------------------------------------
class StatsResponse(BaseModel):
    """Aggregate stats from telemt (GET /api/stats)."""

    active_users: int
    total_connections: int
    total_traffic: int
class LabelStats(BaseModel):
    """Per-label connection/traffic stats (GET /api/stats/labels).

    Connections and traffic are aggregated per labelled link.
    """

    label: str
    telemt_username: str
    connections: int = 0
    ip_count: int = 0
class LabelStatsListResponse(BaseModel):
    """List of per-label stats (GET /api/stats/labels)."""

    items: list[LabelStats]
# -- Health model --------------------------------------------------------------
class HealthResponse(BaseModel):
    """Health check response (GET /api/health)."""

    status: str = "ok"
