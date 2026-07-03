---
id: TKT-005
type: ticket
status: in_review
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-002@0.1.0, TKT-003@0.1.0]
estimate: L
created: 2026-07-02
---

# TKT-005@0.1.0: Admin API — FastAPI Backend

## §1 Goal

Implement the FastAPI admin API with JWT authentication, user management, labelled link CRUD, and stats endpoints.

## §2 In Scope

- `api/main.py` — FastAPI app factory with CORS, exception handlers.
- `api/auth.py` — JWT auth: login endpoint, token creation/validation, password hashing (bcrypt).
- `api/routes/users.py` — GET /api/users (paginated), POST /api/users/{username}/disable, POST /api/users/{username}/enable.
- `api/routes/links.py` — GET /api/links, POST /api/links, DELETE /api/links/{id}.
- `api/routes/stats.py` — GET /api/stats, GET /api/stats/labels.
- `api/routes/health.py` — GET /api/health.
- `api/deps.py` — FastAPI dependencies (get_db, get_current_user, get_telemt_client).
- `api/schemas.py` — Pydantic request/response models for API endpoints.
- Rate limiting on `/api/auth/login` (5 attempts/min per IP).
- Tests: `tests/test_api_auth.py`, `tests/test_api_users.py`, `tests/test_api_links.py`, `tests/test_api_stats.py`.

## §3 NOT In Scope

- Frontend (TKT-007@0.1.1).
- Bot handlers (TKT-004@0.1.1).
- Deploy scripts (TKT-010@0.1.0).
- User tier logic (R18 extension point only).
- Admin user management endpoints (admin users created via deploy script CLI only in MVP).

## §4 Inputs

- ARCH-001@0.1.1 §3 C3 (API interface/contract)
- ARCH-001@0.1.1 §4 (Database schema, Telemt API contract)
- ADR-002@0.1.0 (JWT auth)
- ADR-006@0.1.0 (async database access)

## §5 Outputs

- `api/main.py`
- `api/auth.py`
- `api/routes/__init__.py`
- `api/routes/users.py`
- `api/routes/links.py`
- `api/routes/stats.py`
- `api/routes/health.py`
- `api/deps.py`
- `api/schemas.py`
- `tests/test_api_auth.py`
- `tests/test_api_users.py`
- `tests/test_api_links.py`
- `tests/test_api_stats.py`

## §6 Acceptance Criteria

- [ ] AC1 — `POST /api/auth/login` returns JWT on valid credentials, 401 on invalid.
- [ ] AC2 — All endpoints except `/api/auth/login` and `/api/health` require valid JWT.
- [ ] AC3 — `GET /api/users` returns paginated list with telemt stats merged.
- [ ] AC4 — `POST /api/links` creates telemt user + DB record, returns proxy link.
- [ ] AC5 — `GET /api/stats/labels` returns per-label connection/traffic stats.
- [ ] AC6 — Rate limiter returns 429 after 5 failed login attempts from same IP within 1 minute.
- [ ] AC7 — 502 returned when telemt API is unreachable (not 500).
- [ ] AC8 — `mypy --strict` passes on all `api/` files.
- [ ] AC9 — Tests achieve ≥80% coverage.

## §7 Constraints

- No new dependencies beyond TKT-001@0.1.1. FastAPI, python-jose, passlib already declared.
- Rate limiting: use `slowapi` or custom middleware (add `slowapi` to dev deps if needed).

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-03 opencode-executor: started
- 2026-07-03 opencode-executor: in_review; tests 41 pass; lint clean; typecheck clean; coverage 95%
- 2026-07-03 executor: fix F-H1 (add types-python-jose for mypy strict)
