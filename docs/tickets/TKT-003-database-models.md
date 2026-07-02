---
id: TKT-003
type: ticket
status: in_review
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-001@0.1.1]
estimate: M
created: 2026-07-02
---

# TKT-003@0.1.0: Database Models and Migrations

## §1 Goal

Implement SQLAlchemy 2.x async ORM models for `admin_users`, `proxy_users`, and `labelled_links` tables, plus Alembic migration infrastructure.

## §2 In Scope

- `telemt_proxy/models.py` — SQLAlchemy 2.x async ORM models: `AdminUser`, `ProxyUser`, `LabelledLink`.
- `telemt_proxy/database.py` — `create_async_engine()`, `async_sessionmaker`, `get_db_session()` dependency.
- `alembic.ini` + `alembic/env.py` (async-compatible) + initial migration.
- `tests/test_models.py` — unit tests with in-memory SQLite or test PostgreSQL.

## §3 NOT In Scope

- API endpoints that use these models (TKT-005@0.1.0).
- Bot handlers that use these models (TKT-004@0.1.1).
- Any business logic beyond model definitions.

## §4 Inputs

- ARCH-001@0.1.1 §4 (Database schema)
- ADR-006@0.1.0 (async database access rationale)

## §5 Outputs

- `telemt_proxy/models.py`
- `telemt_proxy/database.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/001_initial.py`
- `tests/test_models.py`

## §6 Acceptance Criteria

- [ ] AC1 — `AdminUser` model has fields: id, username (unique), password_hash, is_active, created_at.
- [ ] AC2 — `ProxyUser` model has fields: id, telemt_username (unique, varchar(16)), telegram_id_hash, created_at, is_active, source.
- [ ] AC3 — `LabelledLink` model has fields: id, label (unique), telemt_username (FK), proxy_link, created_at, is_active.
- [ ] AC4 — `create_async_engine()` accepts `DATABASE_URL` env var with pool_size=5, max_overflow=10.
- [ ] AC5 — Alembic migration `001_initial.py` creates all three tables.
- [ ] AC6 — `alembic upgrade head` runs without errors against a test PostgreSQL.
- [ ] AC7 — No raw SQL strings in any model or migration file (INV-ORM).
- [ ] AC8 — `mypy --strict` passes on all outputs.

## §7 Constraints

- No new dependencies. SQLAlchemy, asyncpg, alembic already in TKT-001@0.1.1.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 opencode-executor: started
- 2026-07-02 opencode-executor: in_review; tests 51 pass; lint clean; typecheck clean
- 2026-07-02 executor: fix DATABASE_URL default + greenlet dev dep
