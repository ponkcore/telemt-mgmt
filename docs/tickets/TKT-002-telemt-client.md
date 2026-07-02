---
id: TKT-002
type: ticket
status: done
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-001@0.1.1]
estimate: M
created: 2026-07-02
---

# TKT-002@0.1.0: TelemtClient — Async httpx Wrapper for Telemt API

## §1 Goal

Implement `TelemtClient` — a typed async httpx wrapper for telemt's REST API — as the single source of truth for all telemt communication.

## §2 In Scope

- `telemt_proxy/client.py` — `TelemtClient` class with async context manager, typed methods for: `create_user`, `list_users`, `get_user`, `disable_user`, `enable_user`, `rotate_secret`, `get_stats_summary`, `get_active_ips`, `get_connections_summary`.
- `telemt_proxy/exceptions.py` — `TelemtAPIError` (base), `TelemtConnectionError`, `TelemtAuthError`, `TelemtNotFoundError`.
- `telemt_proxy/schemas.py` — Pydantic response models: `TelemtUser`, `TelemtStats`, `TelemtConnection`.
- `tests/test_client.py` — unit tests with httpx mock (respx or pytest-httpx).
- Explicit timeouts (10s connect, 30s read) per INV-TIMEOUT.
- `auth_header` sent on every request per INV-AUTH.

## §3 NOT In Scope

- Database models or migrations (TKT-003@0.1.0).
- Bot Router handlers (TKT-004@0.1.1).
- Admin API endpoints (TKT-005@0.1.0).
- `PATCH /v1/config` endpoint wrapping (not needed for MVP — config managed via deploy scripts).

## §4 Inputs

- ARCH-001@0.1.1 §3 C1 (TelemtClient interface/contract)
- ARCH-001@0.1.1 §4 (Telemt API contract table)
- ADR-004@0.1.1 (telemt client wrapper rationale)

## §5 Outputs

- `telemt_proxy/client.py`
- `telemt_proxy/exceptions.py`
- `telemt_proxy/schemas.py`
- `tests/test_client.py`

## §6 Acceptance Criteria

- [ ] AC1 — `TelemtClient` implements all 9 methods listed in ARCH-001@0.1.1 §3 C1.
- [ ] AC2 — All methods return typed Pydantic models, not raw dicts.
- [ ] AC3 — `TelemtClient` works as `async with TelemtClient(...) as client:` context manager.
- [ ] AC4 — Explicit timeouts configured: 10s connect, 30s read.
- [ ] AC5 — `auth_header` is sent as `Authorization` header on every request.
- [ ] AC6 — `TelemtConnectionError` raised on network errors; `TelemtAuthError` on 401/403; `TelemtNotFoundError` on 404.
- [ ] AC7 — `mypy --strict` passes on `telemt_proxy/client.py`, `telemt_proxy/exceptions.py`, `telemt_proxy/schemas.py`.
- [ ] AC8 — Tests achieve ≥80% coverage on `client.py`.

## §7 Constraints

- No new dependencies beyond those in TKT-001@0.1.1. httpx and pydantic already declared.
- Test dependency: respx or pytest-httpx (add to dev dependencies if not present).

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 opencode-executor: started TKT-002 implementation.
- 2026-07-02 opencode-executor: in_review; tests 30 pass; lint clean; typecheck clean; client.py coverage 100%.
- 2026-07-02 opencode-orchestrator: merged in 554487e; RV-CODE-002 verdict=pass; 0 Highs, 0 Mediums, 2 Lows.
