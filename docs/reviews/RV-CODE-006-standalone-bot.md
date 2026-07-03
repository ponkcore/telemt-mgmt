---
id: RV-CODE-006
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/10"
ticket_ref: TKT-006@0.1.0
status: in_review
created: 2026-07-03
---

# RV-CODE-006: review of TKT-006 Standalone Bot (PR #10)

**Verdict:** pass_with_changes
**Summary:** All acceptance criteria are met and project checks pass; one Low finding (docstring/implementation mismatch) and one environmental Medium finding (untracked backlog file blocking docs-CI) need addressing.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `python -m bot` starts the bot (or exits 1 on missing env): `bot/__main__.py:9-10` delegates to `bot/main.py:154-155` `main()`; `bot/main.py:127-152` exits code 1 when `BotConfig.from_env()` raises `KeyError` (tested in `tests/test_bot.py::TestMainEntryPoint`).
- AC2 — Bot includes the telemt_proxy Router via `dp.include_router(router)`: `bot/main.py:102` `dp.include_router(router)` (tested in `tests/test_bot.py::TestSetupBot::test_dispatcher_includes_router`).
- AC3 — Integration example in docstring shows ≤3 lines to embed: `bot/main.py:18-25` docstring contains the 3-line core integration pattern (tested in `tests/test_bot.py::TestEmbedDocstring`).
- AC4 — All config via env vars (7 listed): `bot/config.py:66-74` reads `BOT_TOKEN`, `TELEMT_API_URL`, `TELEMT_AUTH_HEADER`, `TELEMT_PROXY_SERVER`, `TELEMT_PROXY_PORT`, `HASHING_SALT`, `DATABASE_URL` (tested in `tests/test_bot.py::TestBotConfigFromEnv` and `tests/test_bot.py::TestAllEnvVars`).
- AC5 — `mypy --strict` passes: `uv run mypy --strict bot/` reports "Success: no issues found in 4 source files".

## Findings
### High (block merge)
- *None.*

### Medium (fix or backlog)
- F-M1: `docs/backlog/BACKLOG-002-environment-awareness-for-agents.md` is an untracked workspace artifact (not in this PR) and causes `scripts/validate_docs.py` to fail with dangling/un-version-pinned `PRD-1` references. Remove or fix the file before merging so docs-CI is green. This is not a defect introduced by PR #10, but it currently blocks the docs validation gate.

### Low (optional)
- F-L1: `bot/config.py:1` docstring says "Pydantic Settings class", but `BotConfig` is implemented as a plain `@dataclass(frozen=True, slots=True)`. The implementation correctly reads env vars and respects the §7 "No new dependencies" constraint (Pydantic Settings would require `pydantic-settings`), but the docstring should be updated to avoid misleading readers.
- F-L2: `bot/main.py:86` creates an `AsyncEngine` in `setup_bot()` but never disposes it. For a long-lived process this is minor, but consider disposing the engine on shutdown for cleaner resource management.

## Red-team probes (one line each; N/A allowed)
- error_paths: Missing env handled (exit 1); KeyboardInterrupt/SystemExit swallowed gracefully; other runtime exceptions propagate unhandled (acceptable for MVP reference bot).
- concurrency: Single asyncio long-polling loop; no shared mutable state or background tasks introduced.
- input_validation: `TELEMT_PROXY_PORT` cast with `int()` without format validation; non-numeric value raises `ValueError` rather than a friendly error.
- prompt_injection: N/A (no LLM or prompt handling).
- authz_isolation: No admin commands in this component; end-user-only bot flow defers authz to `telemt_proxy` Router and telemt API.
- secrets: All secrets read from env vars; no hardcoded secrets or `.env` committed.
- observability: Basic logging only; no metrics or structured observability added in this ticket.
- rollback: N/A (no stateful deployment or migration logic in this ticket).
- dns_failover: N/A (link building uses configured `TELEMT_PROXY_SERVER` FQDN per INV-DOMAIN).
