"""ProxyConfig — dataclass for router configuration.

Per ADR-001@0.1.2, the ``telemt_proxy`` package uses dependency injection
for all configuration. ``ProxyConfig`` carries all configuration needed by
the standalone bot and the embeddable router.

Per ARCH-001@0.2.1 §3 C1, ``ProxyConfig`` has 5 fields: ``server``,
``port``, ``salt``, ``auth_header``, and ``base_url``. All 5 fields are
intentional — while ``auth_header`` and ``base_url`` are consumed by
``TelemtClient`` (not the router itself), they are included on
``ProxyConfig`` so the standalone bot can construct everything from a
single config object (M6 design intent).

The config is constructed by the host bot (or standalone bot) and passed
to ``create_router()``. It has no side effects on import (INV-EMBED).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    """Configuration for the proxy-link distribution router.

    All 5 fields are documented in ARCH-001@0.2.1 §3 C1 and are
    intentionally kept together for single-object configuration (M6).

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
