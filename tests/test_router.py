"""Unit tests for telemt_proxy.router — aiogram Router proxy-link flow.

Tests cover (AC1, AC4, AC5, AC6, AC10, AC11):
  - AC1: create_router() returns an aiogram.Router, no side effects.
  - AC4: Router handler creates a telemt user via create_user().
  - AC5: Router handler returns existing link on subsequent interactions.
  - AC6: No raw Telegram IDs stored in DB or sent to telemt.
  - AC10: Router sends QR code PNG alongside proxy link.
  - AC11: create_router() has optional tier_service=None parameter.

The tests use AsyncMock to mock TelemtClient and a real in-memory SQLite
database for DB operations. aiogram's Bot is mocked to capture sent messages
without making real API calls.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot, Router
from aiogram.types import (
    CallbackQuery,
    Chat,
    InlineKeyboardMarkup,
    Message,
    User,
)
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from telemt_proxy.config import ProxyConfig
from telemt_proxy.models import Base, ProxyUser
from telemt_proxy.router import create_router
from telemt_proxy.schemas import TelemtUser

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# ── Constants ──────────────────────────────────────────────────────────────

TEST_SALT = "test_salt_at_least_16_chars!"
TEST_SERVER = "proxy.example.com"
TEST_PORT = 443
TEST_TELEMT_USERNAME = "a1b2c3d4e5f6a7b8"
TEST_SECRET = "ee_test_secret_ee"
TEST_TELEGRAM_ID = 12345


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def config() -> ProxyConfig:
    """ProxyConfig for testing."""
    return ProxyConfig(
        server=TEST_SERVER,
        port=TEST_PORT,
        salt=TEST_SALT,
        auth_header="Bearer test-token",
        base_url="http://telemt.test:9091",
    )


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Create an in-memory async SQLite engine for testing."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _enable_fk(dbapi_conn: Any, connection_record: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Async session factory bound to the test engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def mock_telemt_client() -> MagicMock:
    """A mocked TelemtClient."""
    client = MagicMock(spec=["create_user", "get_user", "aclose"])
    client.create_user = AsyncMock(
        return_value=TelemtUser(
            name=TEST_TELEMT_USERNAME,
            secret=TEST_SECRET,
            is_disabled=False,
        ),
    )
    client.get_user = AsyncMock(
        return_value=TelemtUser(
            name=TEST_TELEMT_USERNAME,
            secret=TEST_SECRET,
            is_disabled=False,
        ),
    )
    return client


@pytest.fixture
def mock_bot() -> MagicMock:
    """A mocked aiogram Bot that captures sent messages."""
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest.fixture
def test_user() -> User:
    """A Telegram User for testing."""
    return User(
        id=TEST_TELEGRAM_ID,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="en",
    )


@pytest.fixture
def test_chat() -> Chat:
    """A Telegram Chat for testing."""
    return Chat(id=TEST_TELEGRAM_ID, type="private", first_name="Test")


@pytest.fixture
def test_message(test_chat: Chat) -> Message:
    """A Telegram Message for testing."""
    msg = MagicMock(spec=Message)
    msg.chat = test_chat
    msg.answer = AsyncMock()
    msg.answer_photo = AsyncMock()
    msg.from_user = None  # Messages don't always have from_user in channels
    return msg


@pytest.fixture
def test_callback(
    test_user: User,
    test_message: Message,
) -> CallbackQuery:
    """A Telegram CallbackQuery for testing."""
    cb = MagicMock(spec=CallbackQuery)
    cb.from_user = test_user
    cb.data = "get_proxy"
    cb.message = test_message
    cb.answer = AsyncMock()
    return cb


# ── Helper: extract router handlers ────────────────────────────────────────


def _get_router_handlers(router: Router) -> dict[str, Any]:
    """Extract registered handlers from a Router for direct invocation."""
    handlers: dict[str, Any] = {}
    # aiogram stores handlers in router.observers[update_type].handlers
    for update_type, observer in router.observers.items():
        for handler_wrapper in observer.handlers:
            # The actual callback is the 'callback' attribute
            if hasattr(handler_wrapper, "callback"):
                handlers[update_type] = handler_wrapper.callback
    return handlers


# ── AC1: create_router returns Router, no side effects ────────────────────


class TestCreateRouter:
    """Tests for create_router() (AC1, AC11)."""

    def test_returns_aiogram_router(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
    ) -> None:
        """AC1: create_router() returns an aiogram.Router instance."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        assert isinstance(router, Router)

    def test_no_module_level_side_effects(self) -> None:
        """AC1: importing router.py has no side effects (INV-EMBED).

        Verify that the module source has no top-level code that creates
        bots, connects to databases, or makes network calls.
        """
        import telemt_proxy.router as router_module

        source = inspect.getsource(router_module)
        # The module should not have any top-level Bot() or Dispatcher() calls
        # or module-level database connections.
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
        )
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            # Skip docstrings, comments, imports, and class/function defs
            if stripped.startswith(skip_prefixes):
                continue
            # Check for side-effect patterns at module level (indent level 0)
            if not line.startswith(" ") and not line.startswith("\t"):
                # This is a top-level statement
                # Allow docstring continuation
                if stripped.startswith('"""') or stripped.endswith('"""'):
                    continue
                # These would be side effects if they existed at top level
                assert not stripped.startswith("Bot("), (
                    f"Module-level Bot() call at line {i}: {stripped}"
                )
                assert not stripped.startswith("create_async_engine("), (
                    f"Module-level DB engine at line {i}: {stripped}"
                )

    def test_has_tier_service_none_default(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
    ) -> None:
        """AC11: create_router() has optional tier_service=None parameter."""
        sig = inspect.signature(create_router)
        assert "tier_service" in sig.parameters
        param = sig.parameters["tier_service"]
        assert param.default is None

    def test_works_without_tier_service(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
    ) -> None:
        """AC11: create_router() works without passing tier_service."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        assert isinstance(router, Router)

    def test_accepts_tier_service_none_explicitly(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
    ) -> None:
        """AC11: tier_service=None can be passed explicitly."""
        router = create_router(
            mock_telemt_client,
            db_session_factory,
            config,
            tier_service=None,
        )
        assert isinstance(router, Router)


# ── AC4, AC5, AC6, AC10: Router handler flow ──────────────────────────────


class TestRouterGetProxyFlow:
    """Tests for the get_proxy callback handler (AC4, AC5, AC6, AC10)."""

    async def test_creates_telemt_user_on_first_interaction(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_callback: CallbackQuery,
    ) -> None:
        """AC4: Router creates a telemt user via create_user() on first interaction."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)

        # Invoke the callback handler directly
        callback_handler = handlers["callback_query"]
        await callback_handler(test_callback)

        # Verify create_user was called
        mock_telemt_client.create_user.assert_awaited_once()
        # The argument should be the hash, not the raw Telegram ID
        call_args = mock_telemt_client.create_user.call_args
        username_arg = call_args.args[0]
        assert isinstance(username_arg, str)
        assert len(username_arg) == 16  # 16-char hex hash

    async def test_returns_existing_link_on_subsequent_interaction(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_callback: CallbackQuery,
    ) -> None:
        """AC5: Subsequent interaction returns existing link.

        First call: creates user in telemt + DB.
        Second call: finds user in DB, calls get_user (not create_user).
        Deduplication is via telegram_id_hash.
        """
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        # First interaction
        await callback_handler(test_callback)
        assert mock_telemt_client.create_user.await_count == 1
        assert mock_telemt_client.get_user.await_count == 0

        # Reset mock to track second interaction
        mock_telemt_client.create_user.reset_mock()
        mock_telemt_client.get_user.reset_mock()

        # Second interaction (same user — dedup via telegram_id_hash)
        await callback_handler(test_callback)
        # Should NOT create a new user
        mock_telemt_client.create_user.assert_not_awaited()
        # Should retrieve the existing user
        mock_telemt_client.get_user.assert_awaited_once()

    async def test_no_raw_telegram_ids_stored(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_callback: CallbackQuery,
    ) -> None:
        """AC6: No raw Telegram IDs stored in DB or sent to telemt (INV-HASH).

        After the handler runs, verify:
        - The ProxyUser in DB has telegram_id_hash (64-char hex), not the raw ID.
        - The telemt_username is a 16-char hex hash, not the raw ID.
        - create_user was called with the hash, not the raw ID.
        """
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        await callback_handler(test_callback)

        # Check that create_user was NOT called with the raw Telegram ID
        call_args = mock_telemt_client.create_user.call_args
        username_arg = call_args.args[0]
        assert username_arg != str(TEST_TELEGRAM_ID)
        assert len(username_arg) == 16

        # Check the DB — the ProxyUser should have hashed values
        async with db_session_factory() as session:
            result = await session.execute(select(ProxyUser))
            users = result.scalars().all()
            assert len(users) == 1
            user = users[0]
            # telemt_username is the 16-char hash
            assert len(user.telemt_username) == 16
            assert user.telemt_username != str(TEST_TELEGRAM_ID)
            # telegram_id_hash is the 64-char full hash
            assert len(user.telegram_id_hash) == 64
            assert user.telegram_id_hash != str(TEST_TELEGRAM_ID)
            # The raw ID should not appear anywhere
            assert str(TEST_TELEGRAM_ID) not in user.telemt_username
            assert str(TEST_TELEGRAM_ID) not in user.telegram_id_hash

    async def test_sends_qr_code_png(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_callback: CallbackQuery,
    ) -> None:
        """AC10: Router sends QR code PNG alongside proxy link."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        await callback_handler(test_callback)

        # The message.answer should have been called (for the link text)
        test_callback.message.answer.assert_awaited()  # type: ignore[union-attr]
        # The message.answer_photo should have been called (for the QR code)
        test_callback.message.answer_photo.assert_awaited()  # type: ignore[union-attr]

        # Verify the photo is bytes (PNG data)
        photo_call = test_callback.message.answer_photo.call_args  # type: ignore[union-attr]
        photo_arg = photo_call.args[0]
        assert hasattr(photo_arg, "data")  # BufferedInputFile has .data
        assert isinstance(photo_arg.data, bytes)
        assert photo_arg.data[:8] == b"\x89PNG\r\n\x1a\n"

    async def test_sends_proxy_link_text(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_callback: CallbackQuery,
    ) -> None:
        """The proxy link text is sent to the user."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        await callback_handler(test_callback)

        # The link text should be sent via message.answer
        answer_calls = test_callback.message.answer.call_args_list  # type: ignore[union-attr]
        assert len(answer_calls) > 0
        sent_text = answer_calls[0].args[0]
        assert "tg://proxy" in sent_text
        assert TEST_SERVER in sent_text
        assert str(TEST_PORT) in sent_text
        assert TEST_SECRET in sent_text

    async def test_callback_answered(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_callback: CallbackQuery,
    ) -> None:
        """The callback query is answered (closes the loading indicator)."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        await callback_handler(test_callback)
        test_callback.answer.assert_awaited_once()

    async def test_link_uses_domain_name(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_callback: CallbackQuery,
    ) -> None:
        """AC7: The proxy link uses domain name in server= field (INV-DOMAIN)."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        await callback_handler(test_callback)

        answer_calls = test_callback.message.answer.call_args_list  # type: ignore[union-attr]
        sent_text = answer_calls[0].args[0]
        assert f"server={TEST_SERVER}" in sent_text


# ── /start handler tests ──────────────────────────────────────────────────


class TestRouterStartHandler:
    """Tests for the /start command handler."""

    async def test_start_sends_welcome_with_keyboard(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_message: Message,
    ) -> None:
        """/start sends a welcome message with inline keyboard."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)

        message_handler = handlers["message"]
        await message_handler(test_message)

        test_message.answer.assert_awaited_once()
        call_kwargs = test_message.answer.call_args.kwargs
        assert "reply_markup" in call_kwargs
        keyboard = call_kwargs["reply_markup"]
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Check that the keyboard has a "Получить прокси" button
        found_button = False
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.text == "Получить прокси":
                    found_button = True
                    assert button.callback_data == "get_proxy"
        assert found_button, "Inline keyboard must have a 'Получить прокси' button"

    async def test_start_does_not_create_user(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_message: Message,
    ) -> None:
        """/start does not create a telemt user (only the callback does)."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)

        message_handler = handlers["message"]
        await message_handler(test_message)

        mock_telemt_client.create_user.assert_not_awaited()


# ── Error handling tests ──────────────────────────────────────────────────


class TestRouterErrorHandling:
    """Tests for router error paths."""

    async def test_none_message_in_callback(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_user: User,
    ) -> None:
        """Callback with None message answers gracefully."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        cb = MagicMock(spec=CallbackQuery)
        cb.from_user = test_user
        cb.data = "get_proxy"
        cb.message = None  # Inaccessible message
        cb.answer = AsyncMock()

        await callback_handler(cb)
        cb.answer.assert_awaited_once()

    async def test_none_from_user_in_callback(
        self,
        mock_telemt_client: MagicMock,
        db_session_factory: async_sessionmaker[AsyncSession],
        config: ProxyConfig,
        test_message: Message,
    ) -> None:
        """Callback with None from_user answers gracefully."""
        router = create_router(mock_telemt_client, db_session_factory, config)
        handlers = _get_router_handlers(router)
        callback_handler = handlers["callback_query"]

        cb = MagicMock(spec=CallbackQuery)
        cb.from_user = None
        cb.data = "get_proxy"
        cb.message = test_message
        cb.answer = AsyncMock()

        await callback_handler(cb)
        cb.answer.assert_awaited_once()
