---
id: RV-CODE-004
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/9"
ticket_ref: TKT-004@0.1.1
status: in_review
created: 2026-07-03
---

# RV-CODE-004: review of TKT-004@0.1.1 (PR #9)

**Verdict:** pass_with_changes
**Summary:** All §6 ACs are verifiably met in spirit and the TKT-004@0.1.1 modules pass typecheck, lint, and tests with 100 % coverage; however, the PR deviates from strict scope by touching `pyproject.toml`/`uv.lock`, and the AC2 example input is rejected by the implemented salt-length validation.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10) — **deviation noted**: `pyproject.toml` and `uv.lock` are also modified (see F-M1).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `create_router()` returns an `aiogram.Router` with no module-level side effects: `telemt_proxy/router.py:90-230`; `tests/test_router.py:189-283`.
- AC2 — `hash_telegram_id(12345, <salt>)` returns a deterministic 16-char hex string: `telemt_proxy/hashing.py:21-49`; `tests/test_hashing.py:36-60`.
- AC3 — `build_proxy_link("proxy.example.com", 443, "ee...")` returns `tg://proxy?server=...&port=...&secret=...`: `telemt_proxy/link.py:11-31`; `tests/test_link.py:20-23`.
- AC4 — Router handler creates a telemt user via `TelemtClient.create_user()` on first interaction: `telemt_proxy/router.py:189-200`; `tests/test_router.py:292-313`.
- AC5 — Router returns existing link on subsequent interactions by same Telegram user (dedup via `telegram_id_hash`): `telemt_proxy/router.py:180-184`; `tests/test_router.py:315-346`.
- AC6 — No raw Telegram IDs stored in DB or sent to telemt: `telemt_proxy/router.py:168-200`; `tests/test_router.py:348-388`.
- AC7 — Link uses domain name in `server=` field (INV-DOMAIN): `telemt_proxy/link.py:11-31`; `tests/test_router.py:454-470`.
- AC8 — `mypy --strict` passes on all TKT-004@0.1.1 source files.
- AC9 — Tests achieve ≥80 % coverage on `router.py`, `hashing.py`, `link.py`, `qr.py` (100 % on all four modules).
- AC10 — Router sends QR code image (PNG) alongside proxy link: `telemt_proxy/router.py:216-219`; `telemt_proxy/qr.py:18-44`; `tests/test_qr.py`.
- AC11 — `create_router()` signature includes optional `tier_service=None` parameter: `telemt_proxy/router.py:90-95`; `tests/test_router.py:248-283`.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- **F-M1:** `pyproject.toml` and `uv.lock` are outside the ticket's §5 Outputs but are modified to add `types-qrcode` as a dev dependency. The change is necessary for `mypy --strict` to pass on `telemt_proxy/qr.py`, but it is still a scope deviation from the ticket's declared outputs. Consider updating `§7 Constraints` in `TKT-004@0.1.1` to document the dev dependency, or record the deviation in `§10 Execution Log`.
- **F-M2:** AC2 specifies `hash_telegram_id(12345, "test_salt")`, but the implementation rejects any salt shorter than 16 characters (`telemt_proxy/hashing.py:42-45`). The acceptance criterion cannot be executed literally with the example salt. The intent (deterministic 16-char hex hash) is verified with a 16+ character salt in `tests/test_hashing.py:52-60`. Either relax the validation or update AC2 to use a 16+ character example salt.

### Low  (optional)
- **F-L1:** `telemt_proxy/router.py:164` uses `type: ignore[assignment]` for `callback.message`. The comment explains why, but consider casting via a narrower aiogram helper or typed accessor in a future refactor.
- **F-L2:** Router handler does not catch telemt API failures (e.g., `TelemtAPIError` from `TelemtClient.create_user`). Propagating may be acceptable for MVP, but a future ticket should add user-facing error handling and observability.

## Red-team probes  (one line each; N/A allowed)
- error_paths: Handler guards against `None` message/from_user; telemt API failures are not yet handled in the router (see F-L2).
- concurrency: Async SQLAlchemy session is used correctly inside the handler; no shared mutable state in the router.
- input_validation: Salt length is validated in `hashing.py`; Telegram IDs come from aiogram and are hashed before storage/sending.
- prompt_injection: N/A — no LLM or prompt-based interface.
- authz_isolation: Telemt API auth is encapsulated in `TelemtClient`; no raw auth header handling in the router.
- secrets: Secrets live in `ProxyConfig` and are injected; no secrets in source files.
- observability: No logging or metrics in router; consider adding structured logging in a follow-up.
- rollback: No transaction wrapping telemt API call + DB write; partial failure could leave an orphan telemt user. Document as known limitation / future work.
