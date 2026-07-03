---
id: TKT-010
type: ticket
status: in_review
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-006@0.1.0, TKT-007@0.1.1]
estimate: M
created: 2026-07-02
---

# TKT-010@0.1.0: Deploy Script — Management Server

## §1 Goal

Create an interactive deploy script and Docker Compose for the management server running bot + admin API + admin panel + PostgreSQL.

## §2 In Scope

- `infra/mgmt/deploy-mgmt.sh` — interactive script. Prompts: telemt API URL + auth_header, bot token, database URL (or auto-creates PostgreSQL container), panel domain, admin username + password.
- `infra/mgmt/docker-compose.yml` — Bot + API + Frontend (Angie) + PostgreSQL containers.
- `infra/mgmt/Dockerfile.api` — Dockerfile for FastAPI + bot (single Python image serving both).
- `infra/mgmt/angie.conf.template` — Angie reverse proxy for panel (auto-cert via Let's Encrypt) + API.
- Alembic migration run on startup.
- Initial admin user creation.

## §3 NOT In Scope

- Exit/entry/monitoring deploy (other tickets).
- Grafana/Prometheus on mgmt server (separate monitoring server per PRD).

## §4 Inputs

- ARCH-001@0.1.1 §3 C5 (deploy-mgmt.sh interface)
- ADR-002@0.1.0 (JWT auth — admin user creation)
- ADR-003@0.1.1
- PRD-001@0.3.0 §5 R7, R8

## §5 Outputs

- `infra/mgmt/deploy-mgmt.sh`
- `infra/mgmt/docker-compose.yml`
- `infra/mgmt/Dockerfile.api`
- `infra/mgmt/angie.conf.template`
- `infra/mgmt/.env.example`

## §6 Acceptance Criteria

- [ ] AC1 — `deploy-mgmt.sh` is idempotent.
- [ ] AC2 — Script prompts for telemt API URL, auth_header, bot token, admin credentials.
- [ ] AC3 — PostgreSQL auto-created if DATABASE_URL not provided.
- [ ] AC4 — Alembic migrations run on container startup.
- [ ] AC5 — Admin panel accessible via HTTPS (Angie + Let's Encrypt).
- [ ] AC6 — Bot starts and connects to Telegram via long polling.
- [ ] AC7 — `shellcheck infra/mgmt/deploy-mgmt.sh` passes.

## §7 Constraints

- PostgreSQL image: `postgres:16-alpine`.
- Python base image: `python:3.12-slim`.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-03 opencode-executor: started
- 2026-07-03 opencode-executor: in_review; shellcheck clean; validate_docs OK; all 7 AC met
