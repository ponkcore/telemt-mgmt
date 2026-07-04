---
id: TKT-021
type: ticket
status: done
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: M
created: 2026-07-04
---

# TKT-021: Code bugfixes — async blocking, JWT secret, database factory, CORS, ProxyConfig

## §1 Goal
Fix 5 code-level issues found by RV-CODE-FULL: H1 (blocking bcrypt/QR in async), H2 (JWT secret default), M1 (module-level database engine), M3 (CORS wildcards), M6 (ProxyConfig field drift).

## §2 In Scope
- H1: Wrap `bcrypt.checkpw()`, `bcrypt.hashpw()` in `asyncio.to_thread()` (api/auth.py). Wrap `generate_qr()` call sites in `asyncio.to_thread()` (telemt_proxy/qr.py or call sites in router.py).
- H2: Remove `"dev-secret-change-me"` default from `JWT_SECRET_KEY` in `api/deps.py`. Raise `RuntimeError` if `JWT_SECRET_KEY` is unset or empty.
- M1: Refactor `telemt_proxy/database.py` — replace module-level `engine` and `async_session_factory` with a `create_session_factory(database_url)` function. Update `api/deps.py` and `bot/main.py` to call the factory.
- M3: Restrict CORS `allow_methods` to `["GET", "POST", "DELETE", "OPTIONS"]` and `allow_headers` to `["Authorization", "Content-Type"]` in `api/main.py`.
- M6: ArchSpec §3 C1 already updated to document all 5 fields of `ProxyConfig` (server, port, salt, auth_header, base_url). No executor action needed for this item — code already has 5 fields, ArchSpec now matches.

## §3 NOT In Scope
- Infrastructure files (`infra/`, `scripts/`) — owned by TKT-020@0.2.1, TKT-022@0.2.1, TKT-023@0.2.1.
- Frontend files (`frontend/`) — no code review findings there.
- Test files for unrelated features.
- M2 (exit xver) — subsumed by TKT-020@0.2.1.

## §4 Inputs
- `docs/reviews/RV-CODE-FULL-telemt-mgmt.md` — findings H1, H2, M1, M3, M6
- ARCH-001@0.2.1 §3 C1 (ProxyConfig), §5 INV-ASYNC, INV-SECRETS, INV-EMBED
- GitHub issues #22 (H1), #23 (H2), #24 (M1)

## §5 Outputs
- `api/auth.py` — H1 (async bcrypt), H2 (imports if needed)
- `api/deps.py` — H2 (remove JWT default, add fail-fast check)
- `api/main.py` — M3 (restrict CORS methods/headers)
- `telemt_proxy/qr.py` — H1 (no change to file itself; wrapping at call site)
- `telemt_proxy/router.py` — H1 (wrap `generate_qr()` in `asyncio.to_thread()`)
- `telemt_proxy/database.py` — M1 (factory function)
- `telemt_proxy/config.py` — M6 (verify 5 fields match ArchSpec, add docstring if needed)
- `bot/main.py` — M1 (use factory function for session creation)
- `tests/test_auth.py` — update tests for async bcrypt and JWT fail-fast
- `tests/test_database.py` — update tests for factory function
- `tests/conftest.py` — update fixtures for factory function

## §6 Acceptance Criteria
- [ ] AC1 — `bcrypt.checkpw()` and `bcrypt.hashpw()` are called inside `asyncio.to_thread()`. `verify_password()` and `get_password_hash()` are `async`.
- [ ] AC2 — `generate_qr()` is called via `asyncio.to_thread()` at every call site.
- [ ] AC3 — `JWT_SECRET_KEY` has no default value. App raises `RuntimeError` at import time (or startup) if the env var is missing or empty.
- [ ] AC4 — `telemt_proxy/database.py` has no module-level `engine` or `async_session_factory`. Only a `create_session_factory(database_url: str)` function.
- [ ] AC5 — CORS `allow_methods` lists only `GET`, `POST`, `DELETE`, `OPTIONS`. CORS `allow_headers` lists only `Authorization`, `Content-Type`.
- [ ] AC6 — `ProxyConfig` in `telemt_proxy/config.py` has 5 fields: `server`, `port`, `salt`, `auth_header`, `base_url` (matches ArchSpec §3 C1).
- [ ] AC7 — All existing tests pass. New tests cover async bcrypt and JWT fail-fast.

## §7 Constraints
- No new dependencies.
- `asyncio.to_thread()` requires Python 3.9+ (project already requires 3.12+).
- M1 factory refactor must not break the existing test fixtures (conftest.py creates its own engine). Update conftest to use the new factory.

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
- 2026-07-04 opencode-executor: started; implementing §5 Outputs.
- 2026-07-04 opencode-executor: in_review; tests 217 pass (1 skipped); lint clean; typecheck clean; docs-ci OK.
- 2026-07-04 opencode-orchestrator: merged in 18a1a74; RV-CODE-021-01 verdict=pass_with_changes; F-M1 (pre-existing docs-ci in RV-CODE-023-01) fixed on main before merge.
