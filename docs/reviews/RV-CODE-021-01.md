---
id: RV-CODE-021-01
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/42"
ticket_ref: TKT-021@0.2.1
status: in_review
created: 2026-07-04
---

# RV-CODE-021-01: review of TKT-021@0.2.1 (PR #42)

**Verdict:** pass_with_changes
**Summary:** All 7 §6 acceptance criteria are met and project.jsonc checks (mypy, ruff, pytest) pass, but `docs-ci` fails on a pre-existing unversioned reference in `docs/reviews/RV-CODE-023-01.md` not touched by this PR.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold in changed code.

## Acceptance criteria
- AC1 — `api/auth.py:151-155` wraps `bcrypt.checkpw()` in `asyncio.to_thread()`; `api/auth.py:173-177` wraps `bcrypt.hashpw()`; both `verify_password()` and `get_password_hash()` are `async` (`api/auth.py:137`, `api/auth.py:161`); call site updated to `await` at `api/auth.py:220`.
- AC2 — `telemt_proxy/router.py:211` calls `generate_qr()` via `await asyncio.to_thread(generate_qr, proxy_link)`; only call site in the codebase.
- AC3 — `api/deps.py:42-46` removes the `"dev-secret-change-me"` default and raises `RuntimeError` if `JWT_SECRET_KEY` is unset or empty.
- AC4 — `telemt_proxy/database.py` has no module-level `engine` or `async_session_factory`; only `create_session_factory(database_url: str)` (`telemt_proxy/database.py:38-70`); `api/deps.py:56-61` and `bot/main.py:82-84` call the factory.
- AC5 — `api/main.py:52-53` restricts CORS to `allow_methods=["GET", "POST", "DELETE", "OPTIONS"]` and `allow_headers=["Authorization", "Content-Type"]`.
- AC6 — `telemt_proxy/config.py:44-48` defines `ProxyConfig` with exactly 5 fields (`server`, `port`, `salt`, `auth_header`, `base_url`); docstring documents all 5.
- AC7 — `pytest -q` passes 217 tests (1 skipped); `tests/test_auth.py` and `tests/test_database.py` were added to cover async bcrypt, JWT fail-fast, and the factory refactor.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- F-M1: `python3 scripts/validate_docs.py` fails on `docs/reviews/RV-CODE-023-01.md:10` because it contains the bare reference `TKT-023` (not version-pinned). This file is **not** in this PR diff and the failure is inherited from `main`; docs-ci is therefore red for the branch. Recommendation: fix the unversioned reference on `main` and rebase/merge this branch, or accept that the current docs-ci failure is pre-existing.

### Low  (optional)
- none

## Red-team probes  (one line each; N/A allowed)
- error_paths: `verify_password()` returns `False` on `ValueError`/`TypeError` for malformed hashes (`api/auth.py:157-158`) — graceful degradation preserved.
- concurrency: bcrypt and QR generation now run in `asyncio.to_thread()` — event-loop starvation mitigated (H1).
- input_validation: CORS methods/headers tightened; no new input vectors introduced.
- authz_isolation: JWT secret now fail-fast; no hardcoded fallback. Admin API isolation unchanged.
- secrets: `JWT_SECRET_KEY` no longer has a public default; `api/deps.py:42-46` raises at import if missing.
- observability: No new logging/metrics changes.
- rollback: Revertible by reverting the single TKT-021 commit; no schema or infra changes.
- dns_failover: N/A — no DNS changes.
