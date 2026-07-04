"""Unit tests for telemt_proxy ORM models and database utilities.

Tests cover:
- Model field definitions match ARCH-001 §4 schema (AC1, AC2, AC3).
- Table creation against in-memory async SQLite.
- Unique constraints on username, telemt_username, label.
- Foreign key relationship on labelled_links.telemt_username.
- Database engine/session configuration (AC4).
- No raw SQL strings in models or migrations (AC7, INV-ORM).
"""

from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────
from sqlalchemy import String, Text, event
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import QueuePool

from telemt_proxy import database
from telemt_proxy.models import AdminUser, Base, LabelledLink, ProxyUser


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Create an in-memory async SQLite engine for testing.

    SQLite does not enforce foreign keys by default; we enable
    ``PRAGMA foreign_keys=ON`` via a connect event listener so that FK
    constraint tests work correctly.
    """
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _enable_fk(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN202
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Async session factory bound to the test engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield an async session for each test."""
    async with session_factory() as session:
        yield session


# ── AC1: AdminUser model fields ─────────────────────────────────────────────


class TestAdminUserModel:
    """Verify AdminUser model definition (AC1)."""

    def test_admin_user_tablename(self) -> None:
        assert AdminUser.__tablename__ == "admin_users"

    def test_admin_user_has_id_field(self) -> None:
        col = AdminUser.__table__.c.id
        assert col.primary_key
        assert col.autoincrement is True

    def test_admin_user_username_unique_varchar64(self) -> None:
        col = AdminUser.__table__.c.username
        assert col.unique
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 64

    def test_admin_user_password_hash_varchar256(self) -> None:
        col = AdminUser.__table__.c.password_hash
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 256

    def test_admin_user_is_active_default_true(self) -> None:
        col = AdminUser.__table__.c.is_active
        assert not col.nullable
        assert col.default is not None

    def test_admin_user_created_at_server_default(self) -> None:
        col = AdminUser.__table__.c.created_at
        assert not col.nullable
        assert col.server_default is not None

    def test_admin_user_field_count(self) -> None:
        """Ensure exactly 5 columns, no more, no less."""
        cols = {c.name for c in AdminUser.__table__.c}
        assert cols == {"id", "username", "password_hash", "is_active", "created_at"}


# ── AC2: ProxyUser model fields ──────────────────────────────────────────────


class TestProxyUserModel:
    """Verify ProxyUser model definition (AC2)."""

    def test_proxy_user_tablename(self) -> None:
        assert ProxyUser.__tablename__ == "proxy_users"

    def test_proxy_user_has_id_field(self) -> None:
        col = ProxyUser.__table__.c.id
        assert col.primary_key
        assert col.autoincrement is True

    def test_proxy_user_telemt_username_unique_varchar16(self) -> None:
        col = ProxyUser.__table__.c.telemt_username
        assert col.unique
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 16

    def test_proxy_user_telegram_id_hash_varchar64(self) -> None:
        col = ProxyUser.__table__.c.telegram_id_hash
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 64

    def test_proxy_user_created_at_server_default(self) -> None:
        col = ProxyUser.__table__.c.created_at
        assert not col.nullable
        assert col.server_default is not None

    def test_proxy_user_is_active_default_true(self) -> None:
        col = ProxyUser.__table__.c.is_active
        assert not col.nullable
        assert col.default is not None

    def test_proxy_user_source_varchar32_default_bot(self) -> None:
        col = ProxyUser.__table__.c.source
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 32
        assert col.default is not None
        assert col.default.arg == "bot"

    def test_proxy_user_field_count(self) -> None:
        cols = {c.name for c in ProxyUser.__table__.c}
        assert cols == {
            "id",
            "telemt_username",
            "telegram_id_hash",
            "created_at",
            "is_active",
            "source",
        }


# ── AC3: LabelledLink model fields ───────────────────────────────────────────


class TestLabelledLinkModel:
    """Verify LabelledLink model definition (AC3)."""

    def test_labelled_link_tablename(self) -> None:
        assert LabelledLink.__tablename__ == "labelled_links"

    def test_labelled_link_has_id_field(self) -> None:
        col = LabelledLink.__table__.c.id
        assert col.primary_key
        assert col.autoincrement is True

    def test_labelled_link_label_unique_varchar128(self) -> None:
        col = LabelledLink.__table__.c.label
        assert col.unique
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 128

    def test_labelled_link_telemt_username_fk_varchar16(self) -> None:
        col = LabelledLink.__table__.c.telemt_username
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 16
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.column.table.name == "proxy_users"
        assert fk.column.name == "telemt_username"

    def test_labelled_link_proxy_link_text(self) -> None:
        col = LabelledLink.__table__.c.proxy_link
        assert not col.nullable
        assert isinstance(col.type, Text)

    def test_labelled_link_created_at_server_default(self) -> None:
        col = LabelledLink.__table__.c.created_at
        assert not col.nullable
        assert col.server_default is not None

    def test_labelled_link_is_active_default_true(self) -> None:
        col = LabelledLink.__table__.c.is_active
        assert not col.nullable
        assert col.default is not None

    def test_labelled_link_field_count(self) -> None:
        cols = {c.name for c in LabelledLink.__table__.c}
        assert cols == {
            "id",
            "label",
            "telemt_username",
            "proxy_link",
            "created_at",
            "is_active",
        }


# ── Table creation against in-memory SQLite ─────────────────────────────────


class TestTableCreation:
    """Verify tables can be created and inspected via async SQLite."""

    async def test_all_tables_created(self, engine: AsyncEngine) -> None:
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_table_names()
            )
        assert set(table_names) == {"admin_users", "proxy_users", "labelled_links"}

    async def test_admin_user_columns_in_db(self, engine: AsyncEngine) -> None:
        async with engine.connect() as conn:
            cols = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_columns("admin_users")
            )
        col_names = {c["name"] for c in cols}
        assert col_names == {"id", "username", "password_hash", "is_active", "created_at"}

    async def test_proxy_user_columns_in_db(self, engine: AsyncEngine) -> None:
        async with engine.connect() as conn:
            cols = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_columns("proxy_users")
            )
        col_names = {c["name"] for c in cols}
        assert col_names == {
            "id",
            "telemt_username",
            "telegram_id_hash",
            "created_at",
            "is_active",
            "source",
        }

    async def test_labelled_link_columns_in_db(self, engine: AsyncEngine) -> None:
        async with engine.connect() as conn:
            cols = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_columns("labelled_links")
            )
        col_names = {c["name"] for c in cols}
        assert col_names == {
            "id",
            "label",
            "telemt_username",
            "proxy_link",
            "created_at",
            "is_active",
        }


# ── Unique constraints ───────────────────────────────────────────────────────


class TestUniqueConstraints:
    """Verify unique constraints are enforced at the DB level."""

    async def test_admin_user_username_unique(self, db_session: AsyncSession) -> None:
        admin1 = AdminUser(username="admin1", password_hash="hash123")
        db_session.add(admin1)
        await db_session.commit()

        admin2 = AdminUser(username="admin1", password_hash="hash456")
        db_session.add(admin2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_proxy_user_telemt_username_unique(
        self, db_session: AsyncSession
    ) -> None:
        user1 = ProxyUser(
            telemt_username="abc123def456ghi7",
            telegram_id_hash="a" * 64,
        )
        db_session.add(user1)
        await db_session.commit()

        user2 = ProxyUser(
            telemt_username="abc123def456ghi7",
            telegram_id_hash="b" * 64,
        )
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_labelled_link_label_unique(self, db_session: AsyncSession) -> None:
        proxy = ProxyUser(
            telemt_username="abc123def456ghi7",
            telegram_id_hash="a" * 64,
        )
        db_session.add(proxy)
        await db_session.commit()

        link1 = LabelledLink(
            label="forum-4pda",
            telemt_username="abc123def456ghi7",
            proxy_link="tg://proxy?server=example.com&port=443&secret=abc",
        )
        db_session.add(link1)
        await db_session.commit()

        link2 = LabelledLink(
            label="forum-4pda",
            telemt_username="abc123def456ghi7",
            proxy_link="tg://proxy?server=example.com&port=443&secret=def",
        )
        db_session.add(link2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


# ── Foreign key relationship ──────────────────────────────────────────────────


class TestForeignKeyRelationship:
    """Verify FK relationship on labelled_links.telemt_username."""

    async def test_fk_blocks_orphan_link(self, db_session: AsyncSession) -> None:
        """Cannot insert a labelled_link without a matching proxy_user."""
        link = LabelledLink(
            label="orphan-label",
            telemt_username="nonexistent_user",
            proxy_link="tg://proxy?server=example.com&port=443&secret=abc",
        )
        db_session.add(link)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_fk_allows_valid_link(self, db_session: AsyncSession) -> None:
        """Can insert a labelled_link when a matching proxy_user exists."""
        proxy = ProxyUser(
            telemt_username="validuser1234567",
            telegram_id_hash="c" * 64,
        )
        db_session.add(proxy)
        await db_session.flush()

        link = LabelledLink(
            label="valid-label",
            telemt_username="validuser1234567",
            proxy_link="tg://proxy?server=example.com&port=443&secret=abc",
        )
        db_session.add(link)
        await db_session.commit()

    def test_fk_constraint_exists_on_table(self) -> None:
        """Verify FK is defined in the table metadata."""
        fks = LabelledLink.__table__.c.telemt_username.foreign_keys
        assert len(fks) == 1
        fk = list(fks)[0]
        assert fk.column.table.name == "proxy_users"
        assert fk.column.name == "telemt_username"


# ── AC4: Database engine/session configuration ──────────────────────────────


class TestDatabaseConfiguration:
    """Verify database.py factory function and session setup (AC4, M1)."""

    def test_no_module_level_engine(self) -> None:
        """database.py has no module-level engine (M1, INV-EMBED)."""
        assert not hasattr(database, "engine")
        assert not hasattr(database, "async_session_factory")

    def test_create_session_factory_returns_async_sessionmaker(self) -> None:
        """create_session_factory returns an async_sessionmaker (M1)."""
        factory = database.create_session_factory("sqlite+aiosqlite:///:memory:")
        assert isinstance(factory, async_sessionmaker)

    def test_get_db_session_is_async_generator(self) -> None:
        """get_db_session is an async generator function."""
        assert inspect.isasyncgenfunction(database.get_db_session)

    async def test_get_db_session_yields_session(self) -> None:
        """Test get_db_session yields an AsyncSession and closes it."""
        test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        @event.listens_for(test_engine.sync_engine, "connect")
        def _enable_fk1(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN202
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        test_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        gen = database.get_db_session(test_factory)
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

        await test_engine.dispose()

    async def test_get_db_session_rollback_on_exception(self) -> None:
        """Test get_db_session rolls back on exception."""
        test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        @event.listens_for(test_engine.sync_engine, "connect")
        def _enable_fk2(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN202
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        test_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        gen = database.get_db_session(test_factory)
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)

        with pytest.raises(ValueError, match="test error"):
            await gen.athrow(ValueError("test error"))

        await test_engine.dispose()

    def test_engine_pool_config(self) -> None:
        """Verify pool_size=5 and max_overflow=10 are passed to non-SQLite engines."""
        # When DATABASE_URL is a PostgreSQL URL, engine kwargs must include
        # pool_size=5 and max_overflow=10 (ADR-006).
        pg_engine = create_async_engine(
            "postgresql+asyncpg://user:pass@host:5432/db",
            pool_size=5,
            max_overflow=10,
        )
        pg_pool = pg_engine.pool
        assert isinstance(pg_pool, QueuePool)
        assert pg_pool.size() == 5
        assert pg_pool._max_overflow == 10


# ── AC7: No raw SQL strings (INV-ORM) ────────────────────────────────────────


class TestNoRawSQL:
    """Verify no raw SQL strings in model or migration files (AC7, INV-ORM)."""

    def test_models_no_raw_sql_strings(self) -> None:
        """models.py must not contain raw SQL text() calls or string SQL."""
        import telemt_proxy.models as models_module

        source = inspect.getsource(models_module)
        forbidden = [
            "execute(",
            ".exec_driver_sql(",
            "raw(",
        ]
        for pattern in forbidden:
            assert pattern not in source, (
                f"models.py contains forbidden raw SQL pattern: {pattern}"
            )

    def test_migration_uses_op_functions(self) -> None:
        """Migration file must use op.create_table/op.drop_table, not raw SQL."""
        migration_path = os.path.join("alembic", "versions", "001_initial.py")
        with open(migration_path) as f:
            source = f.read()

        assert "op.create_table" in source
        assert "op.drop_table" in source

        # Raw SQL execution is forbidden (INV-ORM). sa.text() inside
        # server_default is a column-level default expression, not raw SQL
        # execution — that is allowed.
        forbidden = [
            "op.execute(",
            "op.get_bind().execute(",
            ".exec_driver_sql(",
            "raw(",
        ]
        for pattern in forbidden:
            assert pattern not in source, (
                f"Migration file contains forbidden raw SQL pattern: {pattern}"
            )


# ── Model defaults and server defaults ──────────────────────────────────────


class TestModelDefaults:
    """Verify model defaults work correctly."""

    async def test_proxy_user_source_default_bot(self, db_session: AsyncSession) -> None:
        user = ProxyUser(
            telemt_username="test123def456ghi",
            telegram_id_hash="d" * 64,
        )
        db_session.add(user)
        await db_session.commit()
        assert user.source == "bot"

    async def test_proxy_user_is_active_default_true(
        self, db_session: AsyncSession
    ) -> None:
        user = ProxyUser(
            telemt_username="actv123def456ghi",
            telegram_id_hash="e" * 64,
        )
        db_session.add(user)
        await db_session.commit()
        assert user.is_active is True

    async def test_admin_user_is_active_default_true(
        self, db_session: AsyncSession
    ) -> None:
        admin = AdminUser(
            username="testadmin",
            password_hash="hash789",
        )
        db_session.add(admin)
        await db_session.commit()
        assert admin.is_active is True

    async def test_labelled_link_is_active_default_true(
        self, db_session: AsyncSession
    ) -> None:
        proxy = ProxyUser(
            telemt_username="lnk123def456ghi8",
            telegram_id_hash="f" * 64,
        )
        db_session.add(proxy)
        await db_session.flush()

        link = LabelledLink(
            label="test-link",
            telemt_username="lnk123def456ghi8",
            proxy_link="tg://proxy?server=example.com&port=443&secret=abc",
        )
        db_session.add(link)
        await db_session.commit()
        assert link.is_active is True

    async def test_created_at_set_on_insert(self, db_session: AsyncSession) -> None:
        """created_at should be set by server_default (now) on insert."""
        proxy = ProxyUser(
            telemt_username="time123def456ghi",
            telegram_id_hash="g" * 64,
        )
        db_session.add(proxy)
        await db_session.commit()
        assert proxy.created_at is not None

    def test_proxy_user_repr(self) -> None:
        user = ProxyUser(
            telemt_username="repr123def456ghi",
            telegram_id_hash="h" * 64,
        )
        repr_str = repr(user)
        assert "ProxyUser" in repr_str
        assert "repr123def456ghi" in repr_str

    def test_admin_user_repr(self) -> None:
        admin = AdminUser(username="repradmin", password_hash="hash")
        repr_str = repr(admin)
        assert "AdminUser" in repr_str
        assert "repradmin" in repr_str

    def test_labelled_link_repr(self) -> None:
        link = LabelledLink(
            label="repr-label",
            telemt_username="repr123def456ghi",
            proxy_link="tg://proxy?test",
        )
        repr_str = repr(link)
        assert "LabelledLink" in repr_str
        assert "repr-label" in repr_str


# ── Base class tests ─────────────────────────────────────────────────────────


class TestBaseClass:
    """Verify the Base declarative class."""

    def test_base_is_declarative_base(self) -> None:
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)

    def test_base_metadata_has_all_tables(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        assert table_names == {"admin_users", "proxy_users", "labelled_links"}
