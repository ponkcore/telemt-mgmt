"""TelemtClient — async httpx wrapper for the telemt REST API.

This is the ONLY code that makes HTTP calls to telemt (:9091).
All other components (bot, admin API) use this client via dependency
injection, ensuring consistent auth, timeouts, and error handling.

Per ADR-004@0.1.1:
  - Constructor takes base_url, auth_header, timeout (default: 10s connect, 30s read).
  - Implements `async with` context manager for httpx client lifecycle.
  - Returns Pydantic models (not raw dicts) for type safety.
  - Raises typed exceptions for network, auth, and not-found errors.

Invariants enforced:
  - INV-AUTH: auth_header sent as Authorization header on every request.
  - INV-TIMEOUT: explicit timeouts — no infinite waits.
  - INV-ASYNC: all methods are async.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import TracebackType

import httpx

from telemt_proxy.exceptions import (
    TelemtAPIError,
    TelemtAuthError,
    TelemtConnectionError,
    TelemtNotFoundError,
)
from telemt_proxy.schemas import (
    TelemtConnection,
    TelemtStats,
    TelemtUser,
)

# Default timeout: 10s connect, 30s read (INV-TIMEOUT).
DEFAULT_TIMEOUT: httpx.Timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


class TelemtClient:
    """Async httpx wrapper for the telemt REST API.

    Usage::

        async with TelemtClient(
            base_url="http://exit-server:9091",
            auth_header="Bearer my-secret-token",
        ) as client:
            user = await client.create_user("a1b2c3d4e5f6a7b8")
            stats = await client.get_stats_summary()

    All methods return typed Pydantic models and raise typed exceptions
    on failure, enabling ``mypy --strict`` end-to-end.
    """

    def __init__(
        self,
        base_url: str,
        auth_header: str,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        """Initialize the TelemtClient.

        Args:
            base_url: The telemt API base URL (e.g. ``http://exit-server:9091``).
            auth_header: The value for the ``Authorization`` header sent on every
                request (per INV-AUTH).
            timeout: httpx timeout configuration. Defaults to 10s connect,
                30s read (per INV-TIMEOUT).
        """
        self._base_url = base_url.rstrip("/")
        self._auth_header = auth_header
        self._timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    # ── Async context manager ──────────────────────────────────────────────

    async def __aenter__(self) -> TelemtClient:
        """Create the underlying httpx.AsyncClient on context entry."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Authorization": self._auth_header},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the underlying httpx.AsyncClient on context exit."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Internal helpers ───────────────────────────────────────────────────

    def _get_client(self) -> httpx.AsyncClient:
        """Get the active httpx client, creating one if not in a context manager.

        This allows method calls without ``async with`` — a lazy client is
        created on first use and reused until ``aclose()``.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Authorization": self._auth_header},
            )
        return self._client

    @staticmethod
    def _handle_error(exc: Exception) -> TelemtAPIError:
        """Map an httpx exception to a typed TelemtAPIError subclass.

        - httpx.ConnectError (and subclasses) → TelemtConnectionError
        - httpx 401/403 → TelemtAuthError
        - httpx 404 → TelemtNotFoundError
        - other httpx.HTTPStatusError → TelemtAPIError (base)
        - other httpx errors → TelemtConnectionError
        """
        if isinstance(exc, httpx.ConnectError):
            return TelemtConnectionError(f"Cannot connect to telemt API: {exc}")
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status in (401, 403):
                return TelemtAuthError(
                    f"telemt API returned {status}: {exc.response.text}"
                )
            if status == 404:
                return TelemtNotFoundError(
                    f"telemt API returned 404: {exc.response.text}"
                )
            return TelemtAPIError(
                f"telemt API returned {status}: {exc.response.text}"
            )
        if isinstance(exc, httpx.HTTPError):
            return TelemtConnectionError(f"HTTP transport error: {exc}")
        return TelemtAPIError(str(exc))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send an HTTP request and handle errors.

        The Authorization header is set on the client at creation time,
        so every request automatically includes it (INV-AUTH).

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path relative to base_url (e.g. ``/v1/users``).
            json: Optional JSON body for POST/PATCH requests.

        Returns:
            The httpx.Response on success (status < 400).

        Raises:
            TelemtConnectionError: on network errors.
            TelemtAuthError: on 401/403.
            TelemtNotFoundError: on 404.
            TelemtAPIError: on other non-2xx responses.
        """
        client = self._get_client()
        try:
            response = await client.request(method, path, json=json)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise self._handle_error(exc) from exc
        except httpx.HTTPStatusError as exc:
            raise self._handle_error(exc) from exc
        except httpx.HTTPError as exc:
            raise self._handle_error(exc) from exc
        return response

    async def aclose(self) -> None:
        """Close the underlying httpx client if it was lazily created."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── User management methods ────────────────────────────────────────────

    async def create_user(self, username: str) -> TelemtUser:
        """Create a telemt proxy user.

        POST /v1/users with body ``{"name": "<username>"}``.
        Returns the user object including the generated secret.

        Args:
            username: The SHA256 hash used as the telemt username.

        Returns:
            TelemtUser with name and secret populated.
        """
        response = await self._request("POST", "/v1/users", json={"name": username})
        return TelemtUser.model_validate(response.json())

    async def list_users(self) -> list[TelemtUser]:
        """List all telemt proxy users.

        GET /v1/users. Returns an array of user objects.

        Returns:
            List of TelemtUser objects (without secrets).
        """
        response = await self._request("GET", "/v1/users")
        data = response.json()
        return [TelemtUser.model_validate(item) for item in data]

    async def get_user(self, username: str) -> TelemtUser:
        """Get a single telemt proxy user.

        GET /v1/users/{username}. Returns the user object.
        Raises TelemtNotFoundError if the user does not exist.

        Args:
            username: The telemt username to look up.

        Returns:
            TelemtUser for the given username.
        """
        response = await self._request("GET", f"/v1/users/{username}")
        return TelemtUser.model_validate(response.json())

    async def disable_user(self, username: str) -> None:
        """Disable a telemt proxy user.

        POST /v1/users/{username}/disable. No response body.

        Args:
            username: The telemt username to disable.
        """
        await self._request("POST", f"/v1/users/{username}/disable")

    async def enable_user(self, username: str) -> None:
        """Enable a telemt proxy user.

        POST /v1/users/{username}/enable. No response body.

        Args:
            username: The telemt username to enable.
        """
        await self._request("POST", f"/v1/users/{username}/enable")

    async def rotate_secret(self, username: str) -> str:
        """Rotate a telemt user's secret.

        POST /v1/users/{username}/rotate-secret. Returns the new secret.
        The old secret is invalidated; existing proxy links stop working.

        Args:
            username: The telemt username whose secret to rotate.

        Returns:
            The new secret string.
        """
        response = await self._request("POST", f"/v1/users/{username}/rotate-secret")
        data: dict[str, Any] = response.json()
        secret: str = data["secret"]
        return secret

    # ── Stats and connections methods ──────────────────────────────────────

    async def get_stats_summary(self) -> TelemtStats:
        """Get aggregate telemt statistics.

        GET /v1/stats/summary. Returns active users, total connections,
        and total traffic.

        Returns:
            TelemtStats with aggregate numbers.
        """
        response = await self._request("GET", "/v1/stats/summary")
        return TelemtStats.model_validate(response.json())

    async def get_active_ips(self) -> list[TelemtConnection]:
        """Get per-user active IP counts.

        GET /v1/stats/users/active-ips. Returns a list of per-user
        connection data with ip_count populated.

        Returns:
            List of TelemtConnection objects with ip_count.
        """
        response = await self._request("GET", "/v1/stats/users/active-ips")
        data = response.json()
        return [TelemtConnection.model_validate(item) for item in data]

    async def get_connections_summary(self) -> list[TelemtConnection]:
        """Get live per-user connection summary.

        GET /v1/runtime/connections/summary. Returns a list of per-user
        connection data with connections populated.

        Returns:
            List of TelemtConnection objects with connections count.
        """
        response = await self._request("GET", "/v1/runtime/connections/summary")
        data = response.json()
        return [TelemtConnection.model_validate(item) for item in data]
