"""JWT authentication for the admin API (C3).

Per ADR-002@0.1.0:
  - POST /api/auth/login accepts {username, password}, validates against
    admin_users table (bcrypt-hashed passwords), returns JWT (HS256, 30-min expiry).
  - Rate limiting: 5 failed attempts per IP per minute -> 429 (per BACKLOG-001,
    uses custom in-memory middleware, NOT slowapi).

Invariants:
  - INV-SECRETS: JWT_SECRET_KEY from env var.
  - INV-ASYNC: password verification and DB access are async.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from sqlalchemy import select

from api.deps import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET_KEY,
    get_db_session,
)
from api.schemas import LoginRequest, TokenResponse
from telemt_proxy.models import AdminUser

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


# -- Rate limiter (custom middleware, per BACKLOG-001) ------------------------

_RATE_LIMIT_MAX_ATTEMPTS: int = 5
_RATE_LIMIT_WINDOW_SECONDS: int = 60


class RateLimiter:
    """In-memory rate limiter for login attempts.

    Tracks timestamps of login attempts per IP address. If an IP has
    made ``_RATE_LIMIT_MAX_ATTEMPTS`` or more attempts within
    ``_RATE_LIMIT_WINDOW_SECONDS``, subsequent attempts are rejected
    with 429.

    Not thread-safe by itself -- relies on the single-threaded asyncio
    event loop for consistency (all access is within async handlers).
    """

    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, ip: str, now: float) -> None:
        """Remove timestamps older than the rate-limit window."""
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        self._attempts[ip] = [t for t in self._attempts[ip] if t > cutoff]

    def is_rate_limited(self, ip: str) -> bool:
        """Check if the IP is currently rate-limited."""
        now = time.monotonic()
        self._cleanup(ip, now)
        return len(self._attempts[ip]) >= _RATE_LIMIT_MAX_ATTEMPTS

    def record_attempt(self, ip: str) -> None:
        """Record a login attempt for the given IP."""
        now = time.monotonic()
        self._cleanup(ip, now)
        self._attempts[ip].append(now)

    def reset(self) -> None:
        """Clear all rate-limit state (for testing)."""
        self._attempts.clear()

    def retry_after(self, ip: str) -> int:
        """Return seconds until the oldest attempt in the window expires."""
        now = time.monotonic()
        self._cleanup(ip, now)
        if not self._attempts[ip]:
            return _RATE_LIMIT_WINDOW_SECONDS
        oldest = self._attempts[ip][0]
        return max(1, int(_RATE_LIMIT_WINDOW_SECONDS - (now - oldest)) + 1)


# Module-level singleton for the rate limiter.
rate_limiter = RateLimiter()


def _get_client_ip(request: Request) -> str:
    """Extract the client IP from the request.

    Checks X-Forwarded-For first (for reverse proxy setups), then
    falls back to the direct client IP.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    if client is not None:
        return client.host
    return "unknown"


def create_access_token(username: str) -> str:
    """Create a JWT access token for the given admin username.

    The token includes:
      - ``sub``: the admin username.
      - ``exp``: expiration timestamp (now + JWT_EXPIRE_MINUTES).

    Args:
        username: The admin username to encode in the token.

    Returns:
        The encoded JWT string.
    """
    expire = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode: dict[str, object] = {
        "sub": username,
        "exp": int(expire.timestamp()),
    }
    encoded: str = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password to check.
        hashed_password: The bcrypt hash from the database.

    Returns:
        True if the password matches the hash.
    """
    try:
        result: bool = bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
        return result
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash string.
    """
    hashed: bytes = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    )
    return hashed.decode("utf-8")


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    # response parameter removed — headers set on HTTPException
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> TokenResponse:
    """Authenticate an admin user and return a JWT access token.

    POST /api/auth/login with body ``{username, password}``.
    On success: returns ``{access_token, token_type}``.
    On invalid credentials: 401.
    On rate limit exceeded: 429 with Retry-After header.

    Rate limiting: 5 failed attempts per IP per minute (AC6).
    """
    client_ip = _get_client_ip(request)

    if rate_limiter.is_rate_limited(client_ip):
        retry_after = rate_limiter.retry_after(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    result = await db.execute(
        select(AdminUser).where(AdminUser.username == body.username)
    )
    admin_user: AdminUser | None = result.scalar_one_or_none()

    if admin_user is None or not admin_user.is_active:
        rate_limiter.record_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(body.password, admin_user.password_hash):
        rate_limiter.record_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(admin_user.username)
    return TokenResponse(access_token=access_token, token_type="bearer")
