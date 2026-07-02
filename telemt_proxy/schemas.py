"""Pydantic v2 response models for telemt API data.

These models are the typed return values of TelemtClient methods.
They parse raw JSON responses from telemt's REST API (:9091) into
type-safe objects, catching integration errors at development time
(mypy --strict).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TelemtUser(BaseModel):
    """A telemt proxy user.

    Fields match the telemt API user object:
    - name: the SHA256(telegram_id + salt)[:16] hash used as the username.
    - secret: the proxy secret returned on create/rotate; absent on list/get.
    - is_disabled: whether the user is currently disabled.
    """

    name: str
    secret: str | None = None
    is_disabled: bool = False


class TelemtStats(BaseModel):
    """Aggregate telemt statistics from GET /v1/stats/summary.

    - active_users: number of users with active connections.
    - total_connections: total number of live connections across all users.
    - total_traffic: total traffic in bytes across all connections.
    """

    active_users: int
    total_connections: int
    total_traffic: int = Field(description="Total traffic in bytes")


class TelemtConnection(BaseModel):
    """Per-user connection data from active-ips and connections-summary endpoints.

    - username: the telemt user hash.
    - ip_count: number of distinct source IPs (from active-ips endpoint).
    - connections: number of live connections (from connections-summary endpoint).
    """

    username: str
    ip_count: int | None = None
    connections: int | None = None
