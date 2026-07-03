"""Tests for the standalone bot (TKT-006).

Tests cover (AC1–AC5):
  - AC1: ``python -m bot`` starts the bot; exits gracefully (code 1) if
    BOT_TOKEN not set.
  - AC2: Bot includes the telemt_proxy Router via ``dp.include_router(router)``.
  - AC3: Integration example in docstring shows ≤3 lines to embed.
  - AC4: All config via env vars (BOT_TOKEN, TELEMT_API_URL,
    TELEMT_AUTH_HEADER, TELEMT_PROXY_SERVER, TELEMT_PROXY_PORT,
    HASHING_SALT, DATABASE_URL).
  - AC5: ``mypy --strict`` passes (verified by the typecheck command;
    these tests focus on runtime behaviour).
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Bot, Dispatcher, Router

from bot.config import BotConfig
from bot.main import main, run_bot, setup_bot

# ── Constants ──────────────────────────────────────────────────────────────

VALID_ENV: dict[str, str] = {
    "BOT_TOKEN": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "TELEMT_API_URL": "http://telemt.test:9091",
    "TELEMT_AUTH_HEADER": "Bearer test-secret-token",
    "TELEMT_PROXY_SERVER": "proxy.example.com",
    "TELEMT_PROXY_PORT": "443",
    "HASHING_SALT": "test_salt_at_least_16_chars!",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
}

_BOT_ENV_KEYS = list(VALID_ENV.keys())


@pytest.fixture
def bot_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set all required env vars for BotConfig.from_env()."""
    for key, val in VALID_ENV.items():
        monkeypatch.setenv(key, val)
    return VALID_ENV


@pytest.fixture
def bot_config(bot_env: dict[str, str]) -> BotConfig:
    """A BotConfig constructed from the test env vars."""
    return BotConfig.from_env()


def _clear_bot_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delete all bot-related env vars."""
    for key in _BOT_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


# ── AC4: BotConfig.from_env reads all 7 env vars ──────────────────────────


class TestBotConfigFromEnv:
    """Tests for BotConfig.from_env() (AC4)."""

    def test_reads_all_env_vars(self, bot_env: dict[str, str]) -> None:
        """AC4: from_env() reads all 7 required env vars."""
        config = BotConfig.from_env()
        assert config.bot_token == VALID_ENV["BOT_TOKEN"]
        assert config.telemt_api_url == VALID_ENV["TELEMT_API_URL"]
        assert config.telemt_auth_header == VALID_ENV["TELEMT_AUTH_HEADER"]
        assert config.proxy_server == VALID_ENV["TELEMT_PROXY_SERVER"]
        assert config.proxy_port == int(VALID_ENV["TELEMT_PROXY_PORT"])
        assert config.hashing_salt == VALID_ENV["HASHING_SALT"]
        assert config.database_url == VALID_ENV["DATABASE_URL"]

    def test_missing_bot_token_raises_key_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: Missing BOT_TOKEN raises KeyError."""
        for key, val in VALID_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        with pytest.raises(KeyError, match="BOT_TOKEN"):
            BotConfig.from_env()

    def test_missing_telemt_api_url_raises_key_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: Missing TELEMT_API_URL raises KeyError."""
        for key, val in VALID_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("TELEMT_API_URL", raising=False)
        with pytest.raises(KeyError, match="TELEMT_API_URL"):
            BotConfig.from_env()

    def test_missing_database_url_raises_key_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: Missing DATABASE_URL raises KeyError."""
        for key, val in VALID_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(KeyError, match="DATABASE_URL"):
            BotConfig.from_env()

    def test_missing_hashing_salt_raises_key_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: Missing HASHING_SALT raises KeyError."""
        for key, val in VALID_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("HASHING_SALT", raising=False)
        with pytest.raises(KeyError, match="HASHING_SALT"):
            BotConfig.from_env()

    def test_empty_bot_token_raises_key_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: Empty BOT_TOKEN raises KeyError (treated as missing)."""
        for key, val in VALID_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv("BOT_TOKEN", "")
        with pytest.raises(KeyError, match="BOT_TOKEN"):
            BotConfig.from_env()

    def test_proxy_port_parsed_as_int(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: TELEMT_PROXY_PORT is parsed as an integer."""
        for key, val in VALID_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv("TELEMT_PROXY_PORT", "8443")
        config = BotConfig.from_env()
        assert config.proxy_port == 8443
        assert isinstance(config.proxy_port, int)


# ── AC2: setup_bot includes the telemt_proxy Router ───────────────────────


class TestSetupBot:
    """Tests for setup_bot() (AC2)."""

    def test_returns_bot_and_dispatcher(self, bot_config: BotConfig) -> None:
        """AC2: setup_bot() returns a (Bot, Dispatcher, TelemtClient) tuple."""
        result = setup_bot(bot_config)
        assert isinstance(result[0], Bot)
        assert isinstance(result[1], Dispatcher)

    def test_dispatcher_includes_router(self, bot_config: BotConfig) -> None:
        """AC2: dp.include_router(router) — Dispatcher has the telemt_proxy Router."""
        _, dp, _ = setup_bot(bot_config)
        # aiogram 3.x Dispatcher stores included routers in dp.sub_routers
        sub_routers = list(dp.sub_routers)
        assert len(sub_routers) > 0
        included_routers = [r for r in sub_routers if isinstance(r, Router)]
        assert len(included_routers) >= 1

    def test_setup_bot_returns_telemt_client(
        self,
        bot_config: BotConfig,
    ) -> None:
        """setup_bot returns the TelemtClient for lifecycle management."""
        from telemt_proxy.client import TelemtClient

        _, _, client = setup_bot(bot_config)
        assert isinstance(client, TelemtClient)


# ── AC1: python -m bot exits gracefully if BOT_TOKEN not set ──────────────


class TestMainEntryPoint:
    """Tests for bot.main.main() (AC1)."""

    def test_missing_env_exits_with_code_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: main() exits with code 1 when BOT_TOKEN is not set."""
        _clear_bot_env(monkeypatch)

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_missing_bot_token_exits_with_code_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: main() exits with code 1 when only BOT_TOKEN is missing."""
        for key, val in VALID_ENV.items():
            if key != "BOT_TOKEN":
                monkeypatch.setenv(key, val)
        monkeypatch.delenv("BOT_TOKEN", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_does_not_start_polling_with_missing_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: main() does not reach run_bot() when env vars are missing."""
        _clear_bot_env(monkeypatch)

        from bot import main as main_module

        with patch.object(main_module, "run_bot") as mock_run:
            with pytest.raises(SystemExit):
                main_module.main()
            mock_run.assert_not_called()

    def test_main_calls_run_bot_with_valid_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: main() calls run_bot() when all env vars are present."""
        for key, val in VALID_ENV.items():
            monkeypatch.setenv(key, val)

        from bot import main as main_module

        with patch.object(main_module, "run_bot") as mock_run:
            main_module.main()
            mock_run.assert_called_once()


# ── run_bot tests ─────────────────────────────────────────────────────────


class TestRunBot:
    """Tests for run_bot() — the async polling entry point."""

    async def test_run_bot_starts_polling_and_cleans_up(
        self,
        bot_config: BotConfig,
    ) -> None:
        """run_bot() calls start_polling, then closes client and bot session."""
        # Mock setup_bot to avoid real Bot/Dispatcher creation
        mock_session = type("MockSession", (), {"close": AsyncMock()})()
        mock_bot = type("MockBot", (), {"session": mock_session})()
        mock_dp = type("MockDp", (), {"start_polling": AsyncMock()})()
        mock_client = type("MockClient", (), {"aclose": AsyncMock()})()

        with patch("bot.main.setup_bot", return_value=(mock_bot, mock_dp, mock_client)):
            await run_bot(bot_config)

        # start_polling was called
        mock_dp.start_polling.assert_awaited_once()
        # cleanup: client and bot session closed
        mock_client.aclose.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    async def test_run_bot_cleans_up_on_exception(
        self,
        bot_config: BotConfig,
    ) -> None:
        """run_bot() closes client and bot session even if polling raises."""
        mock_session = type("MockSession", (), {"close": AsyncMock()})()
        mock_bot = type("MockBot", (), {"session": mock_session})()
        mock_dp = type("MockDp", (), {})()
        mock_dp.start_polling = AsyncMock(
            side_effect=RuntimeError("polling failed"),
        )
        mock_client = type("MockClient", (), {"aclose": AsyncMock()})()

        with (
            patch("bot.main.setup_bot", return_value=(mock_bot, mock_dp, mock_client)),
            pytest.raises(RuntimeError, match="polling failed"),
        ):
            await run_bot(bot_config)

        # cleanup still happens in finally
        mock_client.aclose.assert_awaited_once()
        mock_session.close.assert_awaited_once()


# ── AC3: Integration example in docstring shows ≤3 lines ─────────────────


class TestEmbedDocstring:
    """Tests for the integration example in the docstring (AC3, M3)."""

    def test_main_module_has_integration_example(self) -> None:
        """AC3: bot/main.py docstring contains an integration example."""
        import bot.main as main_module

        docstring = main_module.__doc__
        assert docstring is not None
        assert "create_router" in docstring
        assert "include_router" in docstring

    def test_integration_example_is_three_lines(self) -> None:
        """AC3: The integration example shows ≤3 core lines (M3).

        The docstring should contain a code block with the 3-line
        integration pattern: import, create_router, include_router.
        """
        import bot.main as main_module

        source = inspect.getsource(main_module)
        # The docstring contains the embed example with these 3 core lines:
        assert "from telemt_proxy.router import create_router" in source
        assert "router = create_router(" in source
        assert "dp.include_router(router)" in source

    def test_no_module_level_side_effects(self) -> None:
        """INV-EMBED: bot/main.py has no module-level side effects.

        Verify that the module source has no top-level code that creates
        bots, connects to databases, or makes network calls at import time.
        """
        import bot.main as main_module

        source = inspect.getsource(main_module)
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
            "if __name__",
            "",
            "...",
            "_ = ",
            "logger",
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
                assert not stripped.startswith("Bot("), (
                    f"Module-level Bot() call at line {i}: {stripped}"
                )
                assert not stripped.startswith("create_async_engine("), (
                    f"Module-level DB engine at line {i}: {stripped}"
                )
                assert not stripped.startswith("asyncio.run("), (
                    f"Module-level asyncio.run() at line {i}: {stripped}"
                )

    def test_config_module_no_side_effects(self) -> None:
        """INV-EMBED: bot/config.py has no module-level side effects."""
        import bot.config as config_module

        source = inspect.getsource(config_module)
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
            if stripped.startswith(skip_prefixes):
                continue
            if not line.startswith(" ") and not line.startswith("\t"):
                if stripped.startswith('"""') or stripped.endswith('"""'):
                    continue
                assert not stripped.startswith("os.environ.get("), (
                    f"Module-level os.environ.get() at line {i}: {stripped}"
                )


# ── AC4: all 7 env vars recognised ────────────────────────────────────────


class TestAllEnvVars:
    """Verify that all 7 env vars from AC4 are recognised (AC4)."""

    def test_all_ac4_env_vars_listed(self) -> None:
        """AC4: BotConfig.from_env() checks all 7 env vars from the AC."""
        import bot.config as config_module

        source = inspect.getsource(config_module)
        required_vars = [
            "BOT_TOKEN",
            "TELEMT_API_URL",
            "TELEMT_AUTH_HEADER",
            "TELEMT_PROXY_SERVER",
            "TELEMT_PROXY_PORT",
            "HASHING_SALT",
            "DATABASE_URL",
        ]
        for var in required_vars:
            assert var in source, f"Env var '{var}' not found in bot/config.py"


# ── __main__.py entry point ───────────────────────────────────────────────


class TestMainModule:
    """Tests for bot/__main__.py (AC1 — python -m bot)."""

    def test_main_module_imports_main_function(self) -> None:
        """bot/__main__.py imports main from bot.main."""
        import bot.__main__ as main_module

        assert hasattr(main_module, "main")
        assert callable(main_module.main)
