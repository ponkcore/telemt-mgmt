"""Bot configuration via environment variables (Pydantic Settings).

Per ARCH-001@0.1.2 §3 C2, the standalone bot reads all configuration from
environment variables. This module provides a typed ``BotConfig`` that
validates and groups these variables, so ``bot/main.py`` can construct
``TelemtClient``, ``ProxyConfig``, and the DB session factory from a single
source of truth.

Invariants enforced:
    - INV-SECRETS: all secrets via env vars only; never hardcoded.
    - INV-AUTH: ``TELEMT_AUTH_HEADER`` is required; telemt API is never
      accessed without it.
    - INV-ASYNC: ``DATABASE_URL`` must use an async SQLAlchemy dialect
      (``postgresql+asyncpg://`` or ``sqlite+aiosqlite://``).

The module has NO module-level side effects (INV-EMBED) — ``BotConfig`` is
constructed inside ``main()`` / ``run_bot()``, not at import time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BotConfig:
    """Typed configuration for the standalone bot.

    All fields map 1:1 to environment variables (AC4).

    Attributes:
        bot_token: Telegram bot token from @BotFather.
        telemt_api_url: Base URL of the telemt REST API
            (e.g. ``http://exit-server:9091``).
        telemt_auth_header: Value for the ``Authorization`` header on
            every telemt API call (INV-AUTH).
        proxy_server: Entry server FQDN used in ``tg://proxy`` links
            (INV-DOMAIN — domain name, never raw IP).
        proxy_port: Entry server port for proxy links.
        hashing_salt: Salt for ``sha256(telegram_id + salt)[:16]`` (INV-HASH).
            Must be ≥16 chars and must never change after initial set.
        database_url: SQLAlchemy async connection URL
            (e.g. ``postgresql+asyncpg://user:pass@host:5432/db``).
    """

    bot_token: str
    telemt_api_url: str
    telemt_auth_header: str
    proxy_server: str
    proxy_port: int
    hashing_salt: str
    database_url: str

    @classmethod
    def from_env(cls) -> BotConfig:
        """Construct ``BotConfig`` from environment variables.

        Reads the seven env vars listed in AC4. Raises ``KeyError`` if
        any required variable is missing or empty.

        Raises:
            KeyError: If a required environment variable is not set or is empty.
        """
        import os

        required_vars: list[str] = [
            "BOT_TOKEN",
            "TELEMT_API_URL",
            "TELEMT_AUTH_HEADER",
            "TELEMT_PROXY_SERVER",
            "TELEMT_PROXY_PORT",
            "HASHING_SALT",
            "DATABASE_URL",
        ]
        values: dict[str, str] = {}
        for var_name in required_vars:
            value = os.environ.get(var_name)
            if not value:
                raise KeyError(
                    f"Required environment variable '{var_name}' is not set or empty.",
                )
            values[var_name] = value

        return cls(
            bot_token=values["BOT_TOKEN"],
            telemt_api_url=values["TELEMT_API_URL"],
            telemt_auth_header=values["TELEMT_AUTH_HEADER"],
            proxy_server=values["TELEMT_PROXY_SERVER"],
            proxy_port=int(values["TELEMT_PROXY_PORT"]),
            hashing_salt=values["HASHING_SALT"],
            database_url=values["DATABASE_URL"],
        )
