"""FastAPI dependencies for the admin API (C3).

Provides:
- ``get_db_session`` — re-exports the async DB session dependency from telemt_proxy.
- ``get_current_user`` — validates JWT Bearer token and returns the username.
- ``get_telemt_client`` — constructs a TelemtClient from env vars.

Per ADR-002@0.1.0: JWT (HS256) validation, 30-min expiry.
Per ADR-006@0.1.0: async DB sessions via SQLAlchemy 2.x.
Per INV-AUTH: all telemt API calls include auth_header.
Per INV-ASYNC: all I/O async.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select

from telemt_proxy.client import TelemtClient
from telemt_proxy.database import get_db_session as _get_db_session
from telemt_proxy.models import AdminUser

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Security scheme for Bearer token extraction.
security = HTTPBearer()

# JWT configuration from env vars (INV-SECRETS).
JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = 30

# Telemt client configuration from env vars.
TELEMT_API_URL: str = os.environ.get("TELEMT_API_URL", "http://localhost:9091")
TELEMT_AUTH_HEADER: str = os.environ.get("TELEMT_AUTH_HEADER", "")

# Re-export for use in auth.py and route modules.
get_db_session = _get_db_session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> str:
    """Validate the JWT Bearer token and return the admin username.

    Extracts the Bearer token from the Authorization header, decodes
    the JWT, verifies the ``sub`` claim corresponds to an active admin
    user in the database.

    Args:
        credentials: The Bearer token from the Authorization header.
        db: The async database session.

    Returns:
        The admin username (from the JWT ``sub`` claim).

    Raises:
        HTTPException: 401 if the token is invalid, expired, or the
            user is not found / inactive.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        sub_obj: object | None = payload.get("sub")
        if sub_obj is None or not isinstance(sub_obj, str):
            raise credentials_exception
        username: str = sub_obj
    except JWTError as exc:
        raise credentials_exception from exc

    result = await db.execute(
        select(AdminUser).where(AdminUser.username == username)
    )
    admin_user: AdminUser | None = result.scalar_one_or_none()
    if admin_user is None or not admin_user.is_active:
        raise credentials_exception
    return username


def get_telemt_client() -> TelemtClient:
    """Construct a TelemtClient from environment variables.

    Reads ``TELEMT_API_URL`` and ``TELEMT_AUTH_HEADER`` from env vars.
    The client is used as a context manager within route handlers to
    ensure proper httpx lifecycle management.

    Returns:
        A TelemtClient instance (not yet entered as a context manager).
    """
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    return TelemtClient(
        base_url=TELEMT_API_URL,
        auth_header=TELEMT_AUTH_HEADER,
        timeout=timeout,
    )
