---
id: RV-CODE-005
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/11"
ticket_ref: TKT-005@0.1.0
status: in_review
created: 2026-07-03
---

# RV-CODE-005: review of TKT-005 Admin API (PR #11)

**Verdict:** fail
**Summary:** Implementation covers all functional ACs with 95% test coverage, but `mypy --strict` fails on the `jose` import because `types-python-jose` is missing from dev dependencies, blocking AC8 and the project.jsonc typecheck gate.

Review inputs: ARCH-001@0.1.2 §3 C3, ARCH-001@0.1.2 §4, ADR-002@0.1.0, ADR-006@0.1.0, BACKLOG-001.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
  - Notes: `.coveragerc`, `api/py.typed`, and `tests/conftest.py` are also modified; `tests/conftest.py` is required test infrastructure, the other two are justified dev/type markers (see findings).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [ ] Every §6 AC verifiably met (citations below). — AC8 fails.
- [ ] project.jsonc checks green (typecheck/lint/test). — typecheck fails.
- [x] All project.jsonc invariants hold in the diff.

## Acceptance criteria
- AC1 — `POST /api/auth/login` returns JWT on valid creds, 401 on invalid — `tests/test_api_auth.py:28` (`test_login_valid_credentials`, `test_login_invalid_password`, `test_login_nonexistent_user`).
- AC2 — All endpoints except `/api/auth/login` and `/api/health` require valid JWT — `api/deps.py:48` (`get_current_user`); `api/routes/health.py:16` (no auth); tests `tests/test_api_auth.py:75` and per-route no-auth tests.
- AC3 — `GET /api/users` returns paginated list with telemt stats merged — `api/routes/users.py:33` (`list_users`); `tests/test_api_users.py:43` (`test_list_users_with_data`, `test_list_users_pagination`).
- AC4 — `POST /api/links` creates telemt user + DB record, returns proxy link — `api/routes/links.py:79` (`create_link`); `tests/test_api_links.py:30` (`test_create_link`).
- AC5 — `GET /api/stats/labels` returns per-label stats — `api/routes/stats.py:65` (`get_label_stats`); `tests/test_api_stats.py:110` (`test_get_label_stats_with_data`).
- AC6 — Rate limiter returns 429 after 5 failed login attempts/min — `api/auth.py:47` (`RateLimiter`), `api/auth.py:170` (`login`); `tests/test_api_auth.py:144` (`test_rate_limit_after_5_failed_attempts`). Uses custom middleware, NOT slowapi, per BACKLOG-001.
- AC7 — 502 returned when telemt API is unreachable — `api/main.py:64` (global `TelemtConnectionError` handler); route-level handlers in `api/routes/links.py:122`, `api/routes/stats.py:52`, `api/routes/users.py:86`; tests in `tests/test_api_links.py:87`, `tests/test_api_stats.py:73`, `tests/test_api_users.py:138`.
- AC8 — `mypy --strict` passes on all `api/` files — **FAIL** (`api/auth.py:23`, `api/deps.py:22`: missing stubs for `jose`).
- AC9 — Tests achieve ≥80% coverage — **PASS** at 95% (`uv run pytest tests/test_api_*.py -q --cov=api --cov-report=term-missing`).

## Findings
### High  (block merge)
- F-H1: `mypy --strict` fails on `jose` imports. Missing `types-python-jose` dev dependency causes AC8 and the project.jsonc `typecheck` gate to fail (`api/auth.py:23`, `api/deps.py:22`).
  ```
  api/deps.py:22: error: Library stubs not installed for "jose"  [import-untyped]
  api/auth.py:23: error: Library stubs not installed for "jose"  [import-untyped]
  ```

### Medium  (fix or backlog)
- F-M1: `tests/conftest.py` is not listed in TKT-005@0.1.0 §5 Outputs. It is required test infrastructure, but the executor should have included it in the ticket's §5 or obtained a ticket update before modifying it.

### Low  (optional)
- F-L1: `.coveragerc` is not in §5, but it is a justified deviation: it adds `concurrency = thread, greenlet` needed for correct async coverage measurement. Consider moving the `concurrency` setting into `pyproject.toml` `[tool.coverage.run]` so the file can be removed in a follow-up.
- F-L2: `api/py.typed` is not in §5, but it is a justified type-distribution marker for the `api` package and has no runtime effect.
- F-L3: `api/auth.py` uses `bcrypt` directly instead of the already-declared `passlib` wrapper. This is functionally fine (`passlib[bcrypt]` transitively provides `bcrypt`), but the ticket text mentioned `passlib`; consider aligning with the declared dependency or documenting the rationale.

## Red-team probes  (one line each; N/A allowed)
- error_paths: Handlers catch `TelemtConnectionError` and `TelemtNotFoundError` and map them to 502/404; global handler in `api/main.py:64` covers uncaught connection errors. Good.
- concurrency: `RateLimiter` stores per-IP timestamps in memory; acceptable for a single process but will not rate-limit across multiple workers. Document as known limitation.
- input_validation: Pydantic v2 models in `api/schemas.py` enforce field lengths; path params in `/api/users/{username}/disable` are not validated beyond FastAPI defaults. OK for MVP.
- prompt_injection: N/A — no LLM prompts in this code.
- authz_isolation: JWT validation checks `AdminUser.is_active` (`api/deps.py:92`); single admin role. Good.
- secrets: `JWT_SECRET_KEY`, `TELEMT_AUTH_HEADER`, `DATABASE_URL`, etc. are read from env vars (`api/deps.py:36-42`). No hardcoded secrets in diff.
- observability: Health endpoint exists (`api/routes/health.py:16`). No structured logging/OTel in this PR.
- rollback: N/A — no migrations or irreversible changes in this PR.
- dns_failover: N/A — telemt client uses explicit FQDN configured via `TELEMT_API_URL`.

## Hand-back
```
rv: RV-CODE-005  path: docs/reviews/RV-CODE-005-admin-api.md
verdict: fail
counts: 1 high, 1 medium, 3 low
highs:
  - mypy --strict fails due to missing types-python-jose stubs (F-H1)
recommendation: iterate
```
