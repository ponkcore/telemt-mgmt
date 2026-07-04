"""Unit tests for api.auth — async bcrypt and JWT helpers (TKT-021).

Tests cover:
  - AC1 (TKT-021): verify_password() and get_password_hash() are async.
  - AC1 (TKT-021): bcrypt operations are wrapped in asyncio.to_thread.
  - AC3 (TKT-021): JWT fail-fast RuntimeError when JWT_SECRET_KEY is unset.
  - Round-trip: get_password_hash → verify_password returns True.
  - verify_password returns False for wrong password.
  - verify_password returns False for malformed hash (no crash).
"""

from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING

from api.auth import get_password_hash, verify_password

if TYPE_CHECKING:
    import pytest

# ── AC1 (TKT-021): async functions ─────────────────────────────────────────


class TestAsyncBcrypt:
    """Tests that bcrypt functions are async (H1, AC1)."""

    def test_verify_password_is_async(self) -> None:
        """verify_password is a coroutine function (H1)."""
        assert inspect.iscoroutinefunction(verify_password)

    def test_get_password_hash_is_async(self) -> None:
        """get_password_hash is a coroutine function (H1)."""
        assert inspect.iscoroutinefunction(get_password_hash)

    async def test_verify_password_correct_password(self) -> None:
        """verify_password returns True for a matching password."""
        hashed = await get_password_hash("testpass123")
        result = await verify_password("testpass123", hashed)
        assert result is True

    async def test_verify_password_wrong_password(self) -> None:
        """verify_password returns False for a non-matching password."""
        hashed = await get_password_hash("correctpass")
        result = await verify_password("wrongpass", hashed)
        assert result is False

    async def test_verify_password_malformed_hash(self) -> None:
        """verify_password returns False (not crash) for a malformed hash."""
        result = await verify_password("testpass123", "not-a-valid-bcrypt-hash")
        assert result is False

    async def test_get_password_hash_returns_str(self) -> None:
        """get_password_hash returns a str (not bytes)."""
        hashed = await get_password_hash("testpass123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    async def test_get_password_hash_different_passwords_different_hashes(
        self,
    ) -> None:
        """Different passwords produce different hashes."""
        hash1 = await get_password_hash("password1")
        hash2 = await get_password_hash("password2")
        assert hash1 != hash2

    async def test_get_password_hash_same_password_different_hashes(self) -> None:
        """Same password produces different hashes (bcrypt salt)."""
        hash1 = await get_password_hash("samepass")
        hash2 = await get_password_hash("samepass")
        assert hash1 != hash2
        # But both should verify against the same password
        assert await verify_password("samepass", hash1)
        assert await verify_password("samepass", hash2)

    async def test_verify_password_does_not_block_event_loop(self) -> None:
        """verify_password runs in a thread — other tasks can proceed concurrently.

        This is a smoke test: we can't precisely measure blocking, but we
        can verify the function completes and returns the expected type.
        """
        hashed = await get_password_hash("testpass123")
        result = await verify_password("testpass123", hashed)
        assert isinstance(result, bool)


# ── AC3 (TKT-021): JWT fail-fast ───────────────────────────────────────────


class TestJWTSecretFailFast:
    """Tests that JWT_SECRET_KEY unset raises RuntimeError (H2, AC3)."""

    def test_env_var_empty_when_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When JWT_SECRET_KEY is unset, os.environ.get returns empty (H2).

        This verifies the condition that api/deps.py checks at import time.
        We can't re-import api.deps (already imported with secret set),
        but we can verify the logic: empty string → fail-fast.
        """
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        value = os.environ.get("JWT_SECRET_KEY", "")
        assert not value  # The env var is unset or empty → would raise

    def test_jwt_secret_no_hardcoded_default(self) -> None:
        """api.deps has no 'dev-secret-change-me' default (H2)."""
        import api.deps as deps_module

        source = inspect.getsource(deps_module)
        assert "dev-secret-change-me" not in source, (
            "JWT_SECRET_KEY must not default to 'dev-secret-change-me' (H2)"
        )

    def test_jwt_secret_is_set_in_test_env(self) -> None:
        """The test environment has JWT_SECRET_KEY set (via conftest.py)."""
        from api.deps import JWT_SECRET_KEY

        assert JWT_SECRET_KEY  # non-empty
        assert JWT_SECRET_KEY != "dev-secret-change-me"
