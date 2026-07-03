"""ProxyConfig — dataclass for router configuration.

Per ADR-001@0.1.2, the ``telemt_proxy`` package uses dependency injection
for all configuration. ``ProxyConfig`` carries the server, port, and salt
needed to build proxy links and hash Telegram IDs.

The config is constructed by the host bot (or standalone bot) and passed
to ``create_router()``. It has no side effects on import (INV-EMBED).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    """Configuration for the proxy-link distribution router.

    Attributes:
        server: Entry server FQDN (domain name, never a raw IP — INV-DOMAIN).
            Used in the ``server=`` field of ``tg://proxy`` links.
        port: Entry server port for the ``port=`` field of proxy links.
        salt: Hashing salt for ``sha256(telegram_id + salt)`` (INV-HASH).
            Must be at least 16 characters (ADR-005). Must NEVER change
            once set — changing it would orphan all existing telemt users.
        auth_header: Authorization header value for the telemt REST API
            (INV-AUTH). Used by ``TelemtClient``; included here so the
            standalone bot can construct everything from one config object.
        base_url: Base URL of the telemt REST API (e.g.
            ``http://exit-server:9091``). Used by ``TelemtClient``.
    """

    server: str
    port: int
    salt: str
    auth_header: str
    base_url: str
