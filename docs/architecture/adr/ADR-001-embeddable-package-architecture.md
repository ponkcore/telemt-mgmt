---
id: ADR-001
type: adr
status: accepted
version: 0.1.2
created: 2026-07-02
---

# ADR-001: Embeddable Package Architecture

## Context

PRD-001@0.3.0 §5 R1 and R6 require that the bot functionality be available both as a standalone bot AND as an embeddable pip package that can be included in any existing aiogram bot with 2-3 lines of code. ARCH-001@0.1.2 §3 C1 must decide the package boundary.

## Decision

We will structure `telemt_proxy/` as a standalone Python package exposing an `aiogram.Router` factory function. The package contains:
- `router.py` — `create_router()` returns a configured aiogram Router with all handlers.
- `client.py` — `TelemtClient` async httpx wrapper for telemt API.
- `models.py` — SQLAlchemy 2.x async ORM models.
- `link.py` — proxy link builder.
- `hashing.py` — Telegram ID hashing.
- `exceptions.py` — typed exceptions.
- `config.py` — `ProxyConfig` dataclass for router configuration (server, port, salt).

The package has NO global state, NO singletons, NO module-level side effects. All dependencies are injected via `create_router(telemt_client, db_session_factory, config, tier_service=None)`. This makes it safe to include in any existing bot's Dispatcher.

Embed example:

```python
from telemt_proxy.router import create_router
from telemt_proxy.config import ProxyConfig
config = ProxyConfig(server="proxy.example.com", port=443, salt=os.environ["HASHING_SALT"])
router = create_router(telemt_client, db_session_factory, config)
dp.include_router(router)
```

M3 measures lines to integrate the router into an existing bot that already has `telemt_client` and `db_session_factory` set up. The `config` construction (2 lines) is deployment configuration, not integration. Core integration remains 3 lines: import, create_router, include_router.

## Consequences

- **Positive:** Any aiogram 3.x bot can embed proxy distribution with 3 core lines: import, create router, include router. Meets M3 (≤3 lines). The `config` construction is deployment configuration, not integration.
- **Positive:** `TelemtClient` is reusable by both bot and admin API — single source of truth for telemt communication.
- **Negative / cost:** Dependency injection pattern requires the host bot to set up `TelemtClient`, database session factory, and `ProxyConfig` before creating the router. This is more ceremony than a "just import and go" pattern.
- **Follow-ups:** Every executor must ensure `telemt_proxy/` has no module-level imports that cause side effects. The reviewer checks for this.

## Alternatives considered

- **Monolithic bot with plugin system** — rejected because it forces the host bot to adopt our plugin framework instead of using aiogram's native Router system.
- **Middleware-based approach** — rejected because middleware processes every update, not just proxy-related ones. Router-based approach is more selective.

## Revision History

- 2026-07-02 0.1.2 — aligned create_router() signature with TKT-004@0.1.1 (added config parameter) per RV-ARCH-001-v2.
