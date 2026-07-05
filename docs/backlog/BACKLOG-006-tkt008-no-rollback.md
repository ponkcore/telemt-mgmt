---
id: BACKLOG-006
type: backlog
status: done
target_ticket: TKT-008@0.1.1
created: 2026-07-03
---

# BACKLOG-006: deploy-exit.sh no rollback on failed docker compose up

**Source:** RV-CODE-008 F-M3

**Issue:** `deploy-exit.sh:223-229` runs `docker compose down` before `up` without rollback. A failed `up` leaves the service down with no automatic recovery.

**Resolution:** Use `docker compose up -d` without `down` first (Compose handles container replacement atomically). Or implement a rollback trap that restores the previous config if `up` fails.

**Priority:** Medium

## Resolution

Closed as done (TKT-026@0.1.0). deploy-exit.sh now has a `trap _deploy_rollback ERR`
that runs `docker compose down` if `docker compose up -d` fails. The trap is
set after config generation and removed after successful deploy.
