---
id: TKT-006
type: ticket
status: in_review
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-004@0.1.1]
estimate: S
created: 2026-07-02
---

# TKT-006@0.1.0: Standalone Bot — Reference Implementation

## §1 Goal

Implement a runnable standalone Telegram bot that demonstrates the `telemt_proxy` package integration as a reference implementation.

## §2 In Scope

- `bot/main.py` — entry point: reads env vars, creates TelemtClient + DB session factory, creates Router from C1, sets up Dispatcher, runs long polling.
- `bot/__main__.py` — allows `python -m bot`.
- `bot/config.py` — Pydantic Settings class reading env vars.
- Integration example in docstring/README showing the 3-line embed pattern.
- Tests: `tests/test_bot.py` — basic smoke test (bot starts, router included).

## §3 NOT In Scope

- Admin commands in the bot (admin functions are in the web panel C3/C4).
- Webhook mode (long polling only in MVP).
- Multi-language support.

## §4 Inputs

- ARCH-001@0.1.1 §3 C2 (Standalone bot interface)
- ADR-001@0.1.0 (embeddable package architecture)

## §5 Outputs

- `bot/main.py`
- `bot/__main__.py`
- `bot/config.py`
- `tests/test_bot.py`

## §6 Acceptance Criteria

- [ ] AC1 — `python -m bot` starts the bot (exits gracefully if BOT_TOKEN not set).
- [ ] AC2 — Bot includes the telemt_proxy Router via `dp.include_router(router)`.
- [ ] AC3 — Integration example in docstring shows ≤3 lines to embed in another bot (M3).
- [ ] AC4 — All config via env vars (BOT_TOKEN, TELEMT_API_URL, TELEMT_AUTH_HEADER, TELEMT_PROXY_SERVER, TELEMT_PROXY_PORT, HASHING_SALT, DATABASE_URL).
- [ ] AC5 — `mypy --strict` passes.

## §7 Constraints

- No new dependencies.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-03 opencode-executor: started; clean tree from origin/main.
- 2026-07-03 opencode-executor: in_review; tests 22 pass; lint clean; typecheck clean; coverage 94%.
