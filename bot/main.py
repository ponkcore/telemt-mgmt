"""Standalone Telegram bot entry point — reference implementation.

This module demonstrates the ``telemt_proxy`` package integration as a
runnable bot. It reads environment variables, constructs ``TelemtClient``,
``ProxyConfig``, and the DB session factory, then includes the
``telemt_proxy`` Router in an aiogram ``Dispatcher`` and starts long polling.

Per ARCH-001@0.1.2 §3 C2:
    - Entry point: ``python -m bot`` or ``bot/main.py``.
    - Config via env vars (AC4).
    - Exits with code 1 on missing env vars (AC1).
    - Includes the telemt_proxy Router via ``dp.include_router(router)`` (AC2).

Per INV-EMBED:
    - No module-level side effects. All initialisation happens inside
      ``main()`` / ``run_bot()``, guarded by ``if __name__ == "__main__":``.

Integration example (≤3 core lines, M3):
    >>> from telemt_proxy.router import create_router
    >>> router = create_router(telemt_client, db_session_factory, config)
    >>> dp.include_router(router)

    The ``config`` construction (2 lines) is deployment configuration,
    not integration. Core integration remains 3 lines: import,
    create_router, include_router. See ADR-001@0.1.2 for details.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import BotConfig
from telemt_proxy.client import TelemtClient
from telemt_proxy.config import ProxyConfig
from telemt_proxy.router import create_router

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


def setup_bot(config: BotConfig) -> tuple[Bot, Dispatcher, TelemtClient]:
    """Create and configure the aiogram Bot and Dispatcher.

    Constructs ``TelemtClient``, ``ProxyConfig``, and the DB session
    factory from ``config``, then calls ``create_router()`` and includes
    the resulting Router in the Dispatcher (AC2).

    Args:
        config: A validated ``BotConfig`` from environment variables.

    Returns:
        A ``(Bot, Dispatcher, TelemtClient)`` tuple ready for polling.
        The ``TelemtClient`` is returned so the caller can close it
        after polling stops (INV-ASYNC — no lingering connections).
    """
    # ── TelemtClient (INV-AUTH, INV-TIMEOUT) ─────────────────────────────
    telemt_client = TelemtClient(
        base_url=config.telemt_api_url,
        auth_header=config.telemt_auth_header,
    )

    # ── ProxyConfig (INV-DOMAIN, INV-HASH) ───────────────────────────────
    proxy_config = ProxyConfig(
        server=config.proxy_server,
        port=config.proxy_port,
        salt=config.hashing_salt,
        auth_header=config.telemt_auth_header,
        base_url=config.telemt_api_url,
    )

    # ── DB session factory (INV-ORM, INV-ASYNC) ──────────────────────────
    engine: AsyncEngine = create_async_engine(config.database_url, echo=False)
    db_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # ── Router from telemt_proxy (AC2, M3 ≤3-line integration) ───────────
    router = create_router(telemt_client, db_session_factory, proxy_config)

    # ── Bot + Dispatcher ──────────────────────────────────────────────────
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)  # AC2: Bot includes the telemt_proxy Router

    return bot, dp, telemt_client


async def run_bot(config: BotConfig) -> None:
    """Start the bot with long polling.

    Constructs the Bot and Dispatcher via ``setup_bot()``, then starts
    polling. The ``TelemtClient`` is closed on shutdown (INV-ASYNC —
    no lingering connections).

    Args:
        config: A validated ``BotConfig`` from environment variables.
    """
    bot, dp, telemt_client = setup_bot(config)

    try:
        logger.info("Starting bot polling…")
        await dp.start_polling(bot)
    finally:
        await telemt_client.aclose()
        await bot.session.close()


def main() -> None:
    """Entry point for ``python -m bot``.

    Reads environment variables via ``BotConfig.from_env()``. If any
    required variable is missing, logs the error and exits with code 1
    (AC1 — exits gracefully if BOT_TOKEN not set).

    Per INV-EMBED, this function is only called under
    ``if __name__ == "__main__":`` or from ``bot/__main__.py``.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        config = BotConfig.from_env()
    except KeyError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    try:
        asyncio.run(run_bot(config))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
