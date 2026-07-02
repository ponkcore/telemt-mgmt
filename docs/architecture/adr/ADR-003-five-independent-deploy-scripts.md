---
id: ADR-003
type: adr
status: accepted
created: 2026-07-02
---

# ADR-003: Five Independent Deploy Scripts

## Context

PRD-001@0.3.0 §5 R7 specifies four deploy targets (entry, exit, mgmt, monitoring). The PO decided (decision fork #3) that the one-pager landing page should be deployable on ANY server independently, not tied to exit or mgmt. This creates a fifth deploy target.

## Decision

We will create five independent deploy scripts in `infra/`:
1. `deploy-entry.sh` — Xray VLESS-Reality on entry server (Russia).
2. `deploy-exit.sh` — Telemt + Angie on exit server (EU).
3. `deploy-mgmt.sh` — Bot + API + Panel + PostgreSQL on management server.
4. `deploy-monitoring.sh` — Prometheus + Grafana on monitoring server.
5. `deploy-landing.sh` — One-pager + Angie on any server.

Each script:
- Is self-contained: installs Docker if needed, creates directories, generates configs, starts containers.
- Is idempotent: re-running updates config but doesn't duplicate resources.
- Prompts interactively for required values on first run; reads from `.env` on subsequent runs.
- Produces a `docker-compose.yml` and component-specific configs.
- Stores all secrets in a `.env` file (gitignored).

## Consequences

- **Positive:** Maximum deployment flexibility — each component on any server.
- **Positive:** Operator can start with 2 servers (exit + mgmt) and scale to 5 as needed.
- **Negative / cost:** Five scripts to maintain, potential for config drift between them.
- **Follow-ups:** All scripts share a common `infra/lib/common.sh` for Docker checks, prompt helpers, and .env management. `common.sh` is created in TKT-001@0.1.1 (project scaffold) so it exists before any deploy ticket runs, preserving Wave 2 parallelism.

## Alternatives considered

- **Single deploy script with flags** — rejected because it implies a single server or a specific multi-server topology. Five scripts are more flexible.
- **Ansible/Terraform** — rejected for MVP; too much overhead for 4-5 servers. Extension point: scripts produce configs that Ansible could consume later.

## Revision Log

- 2026-07-02 0.1.1 — moved `common.sh` ownership to TKT-001@0.1.1 (project scaffold) per RV-ARCH-001 finding M3 to preserve Wave 2 parallelism.
