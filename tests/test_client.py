"""Unit tests for TelemtClient — async httpx wrapper for the telemt REST API.

Uses respx to mock httpx requests, verifying:
  - Each method returns the correct typed Pydantic model.
  - The async context manager properly manages the httpx client lifecycle.
  - The auth_header is sent as the Authorization header on every request.
  - Error mapping: connection error → TelemtConnectionError, 401/403 →
    TelemtAuthError, 404 → TelemtNotFoundError, 500 → TelemtAPIError.
  - Timeout configuration (default and custom).

Target: ≥80% coverage on telemt_proxy/client.py.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from telemt_proxy.client import DEFAULT_TIMEOUT, TelemtClient
from telemt_proxy.exceptions import (
    TelemtAPIError,
    TelemtAuthError,
    TelemtConnectionError,
    TelemtNotFoundError,
)
from telemt_proxy.schemas import TelemtConnection, TelemtStats, TelemtUser

# ── Constants ──────────────────────────────────────────────────────────────

BASE_URL = "https://telemt.test:9091"
AUTH_HEADER = "Bearer test-secret-token"


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def client() -> TelemtClient:
    """A TelemtClient instance for use within `async with`."""
    return TelemtClient(base_url=BASE_URL, auth_header=AUTH_HEADER)


# ── Test data ──────────────────────────────────────────────────────────────

USER_JSON = {"name": "a1b2c3d4e5f6a7b8", "secret": "abc123secret", "is_disabled": False}
USER_NO_SECRET_JSON = {"name": "a1b2c3d4e5f6a7b8", "is_disabled": False}
STATS_JSON = {"active_users": 5, "total_connections": 10, "total_traffic": 1024}
ACTIVE_IPS_JSON = [{"username": "a1b2c3d4e5f6a7b8", "ip_count": 3}]
CONNECTIONS_JSON = [{"username": "a1b2c3d4e5f6a7b8", "connections": 2}]


# ── Method return type tests ───────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_create_user_returns_typed_model(client: TelemtClient) -> None:
    """create_user returns a TelemtUser with name and secret."""
    respx.post(f"{BASE_URL}/v1/users").mock(return_value=httpx.Response(200, json=USER_JSON))

    async with client:
        result = await client.create_user("a1b2c3d4e5f6a7b8")

    assert isinstance(result, TelemtUser)
    assert result.name == "a1b2c3d4e5f6a7b8"
    assert result.secret == "abc123secret"
    assert result.is_disabled is False


@pytest.mark.asyncio
@respx.mock
async def test_list_users_returns_typed_list(client: TelemtClient) -> None:
    """list_users returns a list of TelemtUser."""
    respx.get(f"{BASE_URL}/v1/users").mock(
        return_value=httpx.Response(200, json=[USER_NO_SECRET_JSON, USER_NO_SECRET_JSON])
    )

    async with client:
        result = await client.list_users()

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(u, TelemtUser) for u in result)
    assert result[0].name == "a1b2c3d4e5f6a7b8"


@pytest.mark.asyncio
@respx.mock
async def test_get_user_returns_typed_model(client: TelemtClient) -> None:
    """get_user returns a TelemtUser."""
    respx.get(f"{BASE_URL}/v1/users/a1b2c3d4e5f6a7b8").mock(
        return_value=httpx.Response(200, json=USER_NO_SECRET_JSON)
    )

    async with client:
        result = await client.get_user("a1b2c3d4e5f6a7b8")

    assert isinstance(result, TelemtUser)
    assert result.name == "a1b2c3d4e5f6a7b8"


@pytest.mark.asyncio
@respx.mock
async def test_disable_user_returns_none(client: TelemtClient) -> None:
    """disable_user returns None on success."""
    respx.post(f"{BASE_URL}/v1/users/a1b2c3d4e5f6a7b8/disable").mock(
        return_value=httpx.Response(200, json={})
    )

    async with client:
        result = await client.disable_user("a1b2c3d4e5f6a7b8")

    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_enable_user_returns_none(client: TelemtClient) -> None:
    """enable_user returns None on success."""
    respx.post(f"{BASE_URL}/v1/users/a1b2c3d4e5f6a7b8/enable").mock(
        return_value=httpx.Response(200, json={})
    )

    async with client:
        result = await client.enable_user("a1b2c3d4e5f6a7b8")

    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_rotate_secret_returns_string(client: TelemtClient) -> None:
    """rotate_secret returns the new secret string."""
    respx.post(f"{BASE_URL}/v1/users/a1b2c3d4e5f6a7b8/rotate-secret").mock(
        return_value=httpx.Response(200, json={"secret": "newsecret456"})
    )

    async with client:
        result = await client.rotate_secret("a1b2c3d4e5f6a7b8")

    assert isinstance(result, str)
    assert result == "newsecret456"


@pytest.mark.asyncio
@respx.mock
async def test_get_stats_summary_returns_typed_model(client: TelemtClient) -> None:
    """get_stats_summary returns a TelemtStats."""
    respx.get(f"{BASE_URL}/v1/stats/summary").mock(
        return_value=httpx.Response(200, json=STATS_JSON)
    )

    async with client:
        result = await client.get_stats_summary()

    assert isinstance(result, TelemtStats)
    assert result.active_users == 5
    assert result.total_connections == 10
    assert result.total_traffic == 1024


@pytest.mark.asyncio
@respx.mock
async def test_get_active_ips_returns_typed_list(client: TelemtClient) -> None:
    """get_active_ips returns a list of TelemtConnection."""
    respx.get(f"{BASE_URL}/v1/stats/users/active-ips").mock(
        return_value=httpx.Response(200, json=ACTIVE_IPS_JSON)
    )

    async with client:
        result = await client.get_active_ips()

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TelemtConnection)
    assert result[0].username == "a1b2c3d4e5f6a7b8"
    assert result[0].ip_count == 3
    assert result[0].connections is None


@pytest.mark.asyncio
@respx.mock
async def test_get_connections_summary_returns_typed_list(client: TelemtClient) -> None:
    """get_connections_summary returns a list of TelemtConnection."""
    respx.get(f"{BASE_URL}/v1/runtime/connections/summary").mock(
        return_value=httpx.Response(200, json=CONNECTIONS_JSON)
    )

    async with client:
        result = await client.get_connections_summary()

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TelemtConnection)
    assert result[0].username == "a1b2c3d4e5f6a7b8"
    assert result[0].connections == 2
    assert result[0].ip_count is None


# ── Context manager tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_context_manager_lifecycle(client: TelemtClient) -> None:
    """async with creates and closes the underlying httpx client."""
    respx.get(f"{BASE_URL}/v1/users").mock(
        return_value=httpx.Response(200, json=[USER_NO_SECRET_JSON])
    )

    async with client:
        assert client._client is not None
        result = await client.list_users()
    # After context exit, client should be closed (set to None)
    assert client._client is None
    assert len(result) == 1


@pytest.mark.asyncio
@respx.mock
async def test_lazy_client_without_context_manager() -> None:
    """Methods work without `async with` via lazy client creation."""
    respx.get(f"{BASE_URL}/v1/stats/summary").mock(
        return_value=httpx.Response(200, json=STATS_JSON)
    )

    lazy_client = TelemtClient(base_url=BASE_URL, auth_header=AUTH_HEADER)
    result = await lazy_client.get_stats_summary()
    assert isinstance(result, TelemtStats)
    await lazy_client.aclose()


@pytest.mark.asyncio
async def test_aclose_without_context_manager() -> None:
    """aclose() on a lazily-created client closes cleanly."""
    lazy_client = TelemtClient(base_url=BASE_URL, auth_header=AUTH_HEADER)
    await lazy_client.aclose()  # should not raise even if never opened


# ── Auth header tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_auth_header_sent_on_every_request(client: TelemtClient) -> None:
    """Authorization header is set on the client and sent on every request."""
    route = respx.get(f"{BASE_URL}/v1/users").mock(
        return_value=httpx.Response(200, json=[USER_NO_SECRET_JSON])
    )

    async with client:
        await client.list_users()

    assert route.called
    sent_request = route.calls[0].request
    assert sent_request.headers["Authorization"] == AUTH_HEADER


@pytest.mark.asyncio
@respx.mock
async def test_auth_header_sent_on_post(client: TelemtClient) -> None:
    """Authorization header is sent on POST requests too."""
    route = respx.post(f"{BASE_URL}/v1/users").mock(
        return_value=httpx.Response(200, json=USER_JSON)
    )

    async with client:
        await client.create_user("a1b2c3d4e5f6a7b8")

    assert route.called
    sent_request = route.calls[0].request
    assert sent_request.headers["Authorization"] == AUTH_HEADER


# ── Error mapping tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_connection_error_raises_telemt_connection_error(client: TelemtClient) -> None:
    """httpx.ConnectError → TelemtConnectionError."""
    respx.get(f"{BASE_URL}/v1/users").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    async with client:
        with pytest.raises(TelemtConnectionError, match="Cannot connect"):
            await client.list_users()


@pytest.mark.asyncio
@respx.mock
async def test_401_raises_telemt_auth_error(client: TelemtClient) -> None:
    """401 response → TelemtAuthError."""
    respx.get(f"{BASE_URL}/v1/users").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )

    async with client:
        with pytest.raises(TelemtAuthError, match="401"):
            await client.list_users()


@pytest.mark.asyncio
@respx.mock
async def test_403_raises_telemt_auth_error(client: TelemtClient) -> None:
    """403 response → TelemtAuthError."""
    respx.get(f"{BASE_URL}/v1/users").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )

    async with client:
        with pytest.raises(TelemtAuthError, match="403"):
            await client.list_users()


@pytest.mark.asyncio
@respx.mock
async def test_404_raises_telemt_not_found_error(client: TelemtClient) -> None:
    """404 response → TelemtNotFoundError."""
    respx.get(f"{BASE_URL}/v1/users/nonexistent").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    async with client:
        with pytest.raises(TelemtNotFoundError, match="404"):
            await client.get_user("nonexistent")


@pytest.mark.asyncio
@respx.mock
async def test_500_raises_telemt_api_error(client: TelemtClient) -> None:
    """500 response → TelemtAPIError (base, not auth or not-found)."""
    respx.get(f"{BASE_URL}/v1/stats/summary").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    async with client:
        with pytest.raises(TelemtAPIError, match="500"):
            await client.get_stats_summary()


@pytest.mark.asyncio
@respx.mock
async def test_500_not_auth_not_notfound(client: TelemtClient) -> None:
    """500 raises TelemtAPIError, not its subclasses."""
    respx.get(f"{BASE_URL}/v1/stats/summary").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    async with client:
        with pytest.raises(TelemtAPIError) as exc_info:
            await client.get_stats_summary()

    # Ensure it's the base class, not a subclass
    assert type(exc_info.value) is TelemtAPIError


@pytest.mark.asyncio
@respx.mock
async def test_timeout_error_raises_telemt_connection_error(client: TelemtClient) -> None:
    """httpx timeout (a ConnectError subclass in transport) → TelemtConnectionError."""
    respx.get(f"{BASE_URL}/v1/users").mock(
        side_effect=httpx.ReadTimeout("Read timed out")
    )

    async with client:
        with pytest.raises(TelemtConnectionError):
            await client.list_users()


@pytest.mark.asyncio
@respx.mock
async def test_404_on_disable_raises_not_found(client: TelemtClient) -> None:
    """404 on disable_user raises TelemtNotFoundError."""
    respx.post(f"{BASE_URL}/v1/users/nonexistent/disable").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    async with client:
        with pytest.raises(TelemtNotFoundError):
            await client.disable_user("nonexistent")


@pytest.mark.asyncio
@respx.mock
async def test_401_on_rotate_secret_raises_auth_error(client: TelemtClient) -> None:
    """401 on rotate_secret raises TelemtAuthError."""
    respx.post(f"{BASE_URL}/v1/users/a1b2c3d4e5f6a7b8/rotate-secret").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )

    async with client:
        with pytest.raises(TelemtAuthError):
            await client.rotate_secret("a1b2c3d4e5f6a7b8")


# ── Timeout configuration tests ────────────────────────────────────────────


def test_default_timeout_is_10s_connect_30s_read() -> None:
    """DEFAULT_TIMEOUT has 10s connect and 30s read."""
    assert DEFAULT_TIMEOUT.connect == 10.0
    assert DEFAULT_TIMEOUT.read == 30.0


def test_client_uses_default_timeout() -> None:
    """TelemtClient uses DEFAULT_TIMEOUT when no timeout is passed."""
    client = TelemtClient(base_url=BASE_URL, auth_header=AUTH_HEADER)
    assert client._timeout == DEFAULT_TIMEOUT


def test_client_accepts_custom_timeout() -> None:
    """TelemtClient accepts a custom httpx.Timeout."""
    custom_timeout = httpx.Timeout(5.0, connect=5.0, read=15.0, write=5.0, pool=5.0)
    client = TelemtClient(base_url=BASE_URL, auth_header=AUTH_HEADER, timeout=custom_timeout)
    assert client._timeout == custom_timeout
    assert client._timeout.connect == 5.0
    assert client._timeout.read == 15.0


def test_base_url_strips_trailing_slash() -> None:
    """Trailing slash is stripped from base_url."""
    client = TelemtClient(base_url="https://telemt.test:9091/", auth_header=AUTH_HEADER)
    assert client._base_url == "https://telemt.test:9091"


# ── Exception hierarchy tests ──────────────────────────────────────────────


def test_exception_hierarchy() -> None:
    """All telemt exceptions are subclasses of TelemtAPIError."""
    assert issubclass(TelemtConnectionError, TelemtAPIError)
    assert issubclass(TelemtAuthError, TelemtAPIError)
    assert issubclass(TelemtNotFoundError, TelemtAPIError)


# ── Multiple methods in one context ────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_multiple_methods_one_context(client: TelemtClient) -> None:
    """Multiple method calls share the same httpx client within one context."""
    respx.get(f"{BASE_URL}/v1/users").mock(
        return_value=httpx.Response(200, json=[USER_NO_SECRET_JSON])
    )
    respx.get(f"{BASE_URL}/v1/stats/summary").mock(
        return_value=httpx.Response(200, json=STATS_JSON)
    )

    async with client:
        users = await client.list_users()
        stats = await client.get_stats_summary()
        # Same client instance for both calls
        assert client._client is not None

    assert len(users) == 1
    assert stats.active_users == 5


# ── Edge case: non-httpx exception in _handle_error ────────────────────────


def test_handle_error_with_non_httpx_exception() -> None:
    """_handle_error with a non-httpx exception returns TelemtAPIError (base)."""
    client = TelemtClient(base_url=BASE_URL, auth_header=AUTH_HEADER)
    result = client._handle_error(ValueError("unexpected error"))
    assert type(result) is TelemtAPIError
    assert "unexpected error" in str(result)
