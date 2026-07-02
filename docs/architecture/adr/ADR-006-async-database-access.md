---
id: ADR-006
type: adr
status: accepted
created: 2026-07-02
---

# ADR-006: Async Database Access with SQLAlchemy 2.x + asyncpg

## Context

ARCH-001@0.1.0 §3 C1 and C3 require PostgreSQL for labelled links and admin users. The project invariant INV-ORM mandates SQLAlchemy ORM. Both FastAPI and aiogram are async-first frameworks. The PO confirmed (decision fork #5) async access.

## Decision

We will use SQLAlchemy 2.x with the async extension (`sqlalchemy.ext.asyncio`) and `asyncpg` as the database driver:
- `create_async_engine()` with connection pooling (pool_size=5, max_overflow=10).
- `async_sessionmaker` for session factory, injected into Router and API endpoints.
- Alembic for migrations (async-compatible configuration).
- All database operations use `async with session.begin()` for transaction management.
- No raw SQL strings (INV-ORM) — all queries via ORM Query API or `select()` statements.

## Consequences

- **Positive:** Non-blocking database access — event loop stays responsive.
- **Positive:** Natural integration with FastAPI's `Depends()` and aiogram's handler injection.
- **Negative / cost:** Async SQLAlchemy has some quirks (lazy loading doesn't work in async mode; must use `selectinload`/`joinedload`).
- **Negative / cost:** Alembic async configuration is slightly more complex than sync.
- **Follow-ups:** All ORM model relationships must use explicit eager loading strategies.

## Alternatives considered

- **SQLAlchemy sync + psycopg2** — PO rejected; blocks event loop.
- **Raw asyncpg without ORM** — rejected; violates INV-ORM invariant.
- **Tortoise ORM** — rejected; SQLAlchemy is the project standard (invariant).
