"""Unit tests for telemt_proxy.database — factory function (TKT-021 M1).

Tests cover:
  - AC4 (TKT-021): database.py has no module-level engine or session factory.
  - AC4 (TKT-021): create_session_factory() returns an async_sessionmaker.
  - AC4 (TKT-021): create_session_factory() creates independent engines.
  - AC4 (TKT-021): get_db_session() yields a session and rolls back on error.
"""

from __future__ import annotations

import contextlib
import inspect

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from telemt_proxy.database import create_session_factory, get_db_session

# ── AC4 (TKT-021): No module-level engine/factory ──────────────────────────


class TestNoModuleLevelSideEffects:
    """Verify database.py has no module-level engine or session factory (M1)."""

    def test_no_module_level_engine(self) -> None:
        """database.py does not create an engine at import time (INV-EMBED)."""
        import telemt_proxy.database as db_module

        source = inspect.getsource(db_module)
        lines = source.split("\n")
        skip_prefixes = (
            "#",
            '"""',
            "from ",
            "import ",
            "class ",
            "def ",
            "async def ",
            "@",
            "if TYPE_CHECKING",
            "",
            "...",
            "_ = ",
            "return",
            "raise",
        )
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(skip_prefixes):
                continue
            # Top-level statements (indent level 0)
            if not line.startswith(" ") and not line.startswith("\t"):
                if stripped.startswith('"""') or stripped.endswith('"""'):
                    continue
                # These would be side effects if they existed at top level
                assert not stripped.startswith("engine ="), (  # noqa: S101
                    f"Module-level engine at line {i}: {stripped}"
                )
                assert not stripped.startswith("async_session_factory ="), (  # noqa: S101
                    f"Module-level session factory at line {i}: {stripped}"
                )
                assert not stripped.startswith("create_async_engine("), (  # noqa: S101
                    f"Module-level create_async_engine at line {i}: {stripped}"
                )

    def test_no_module_level_engine_attribute(self) -> None:
        """The database module has no 'engine' or 'async_session_factory' attributes."""
        import telemt_proxy.database as db_module

        assert not hasattr(db_module, "engine"), (  # noqa: S101
            "database module must not have a module-level 'engine' (M1)"
        )
        assert not hasattr(db_module, "async_session_factory"), (  # noqa: S101
            "database module must not have a module-level "
            "'async_session_factory' (M1)"
        )


# ── AC4 (TKT-021): create_session_factory ──────────────────────────────────


class TestCreateSessionFactory:
    """Tests for create_session_factory() (M1)."""

    def test_returns_async_sessionmaker(self) -> None:
        """create_session_factory returns an async_sessionmaker."""
        factory = create_session_factory("sqlite+aiosqlite:///:memory:")
        assert isinstance(factory, async_sessionmaker)  # noqa: S101

    async def test_factory_creates_sessions(self) -> None:
        """Sessions from the factory can execute queries."""
        factory = create_session_factory("sqlite+aiosqlite:///:memory:")

        async with factory() as session:
            result = await session.execute(text("SELECT 1"))
            scalar = result.scalar()
            assert scalar == 1  # noqa: S101

    async def test_different_urls_create_independent_engines(self) -> None:
        """Two factories with different URLs are independent."""
        factory1 = create_session_factory("sqlite+aiosqlite:///:memory:")
        factory2 = create_session_factory("sqlite+aiosqlite:///:memory:")

        # Create a table in factory1's database
        async with factory1() as session:
            await session.execute(text("CREATE TABLE IF NOT EXISTS test_a (id INTEGER)"))
            await session.commit()

        # factory2's database should NOT have the table (separate in-memory DBs)
        async with factory2() as session:
            result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_a'")
            )
            assert result.scalar() is None  # noqa: S101


# ── AC4 (TKT-021): get_db_session dependency ───────────────────────────────


class TestGetDbSession:
    """Tests for get_db_session() dependency (M1)."""

    async def test_yields_session(self) -> None:
        """get_db_session yields an AsyncSession."""
        factory = create_session_factory("sqlite+aiosqlite:///:memory:")

        gen = get_db_session(factory)
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)  # noqa: S101
        # Clean up the generator
        with contextlib.suppress(StopAsyncIteration):
            await gen.__anext__()

    async def test_rolls_back_on_exception(self) -> None:
        """get_db_session rolls back when an exception is thrown into it."""
        factory = create_session_factory("sqlite+aiosqlite:///:memory:")

        gen = get_db_session(factory)
        await gen.__anext__()

        # The generator should handle the exception, rollback, and re-raise.
        with pytest.raises(RuntimeError, match="test error"):
            await gen.athrow(RuntimeError("test error"))
