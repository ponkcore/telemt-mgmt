---
id: TKT-012
type: ticket
status: in_review
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-001@0.1.1]
estimate: S
created: 2026-07-02
---

# TKT-012@0.1.0: One-Pager Landing Page + Deploy Script

## §1 Goal

Create a static one-pager landing page with a "Получить прокси" button and a deploy script to install it on any server.

## §2 In Scope

- `infra/landing/html/index.html` — responsive static HTML page. Dark theme, centered layout, "Получить прокси" button linking to bot (t.me/botname). No JavaScript. Bot URL configurable.
- `infra/landing/deploy-landing.sh` — interactive script. Prompts: bot URL (t.me/botname), domain (optional for HTTPS).
- `infra/landing/docker-compose.yml` — Angie container serving static files.
- `infra/landing/angie.conf.template` — Angie config.

## §3 NOT In Scope

- Backend logic (pure static page).
- User registration or authentication.
- Analytics or tracking.

## §4 Inputs

- ARCH-001@0.1.1 §3 C6 (One-pager interface)
- ADR-007@0.1.0 (one-pager as standalone deploy)
- PRD-001@0.3.0 §5 R15

## §5 Outputs

- `infra/landing/html/index.html`
- `infra/landing/deploy-landing.sh`
- `infra/landing/docker-compose.yml`
- `infra/landing/angie.conf.template`
- `infra/landing/.env.example`

## §6 Acceptance Criteria

- [ ] AC1 — `deploy-landing.sh` is idempotent.
- [ ] AC2 — Landing page shows a "Получить прокси" button that links to the bot.
- [ ] AC3 — Bot URL is configurable via deploy script (not hardcoded in HTML).
- [ ] AC4 — Page is responsive (works on mobile).
- [ ] AC5 — No JavaScript required for core functionality.
- [ ] AC6 — `shellcheck infra/landing/deploy-landing.sh` passes.

## §7 Constraints

- Angie Docker image: official.
- No npm/build step — pure static HTML + inline CSS.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 opencode-executor: in_review; tests N/A (no code tests for static infra); shellcheck pass; validate_docs.py pass.
- 2026-07-02 executor: fix F-H1 (optional DOMAIN handling).
