---
id: TKT-013
type: ticket
status: done
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-008@0.1.1]
estimate: M
created: 2026-07-02
---

# TKT-013@0.1.1: Migration Script

## §1 Goal

Implement a migration script that moves a telemt exit server to a new server with <2 minutes downtime and updates DNS.

## §2 In Scope

- `scripts/migrate.sh` — migration script. Steps:
  1. Stop containers on old server.
  2. Tar config/state (`/opt/telemt/` or Docker volumes).
  3. SCP to new server.
  4. Run `deploy-exit.sh` on new server (using transferred config).
  5. Update Cloudflare DNS A-record via API (entry server FQDN → new entry server IP, or exit domain → new exit IP).
  6. Verify health check on new server.
- `scripts/cloudflare-dns.sh` — helper script for Cloudflare DNS A-record update via API.
- Supports both exit server and entry server migration.
- Prompts for: old server IP, new server IP, Cloudflare API token, domain, DNS record ID.

## §3 NOT In Scope

- Database migration (PostgreSQL on mgmt server — not affected by exit/entry migration).
- Zero-downtime migration (target is <2 min, not zero).
- Automatic rollback (manual rollback documented in script output).

## §4 Inputs

- ARCH-001@0.1.1 §3 C5 (migration script interface)
- PRD-001@0.3.0 §5 R9 (migration requirements)
- PRD-001@0.3.0 §7 (DNS: Cloudflare DNS-only, TTL=60)

## §5 Outputs

- `scripts/migrate.sh`
- `scripts/cloudflare-dns.sh`

## §6 Acceptance Criteria

- [ ] AC1 — Script completes full migration cycle in <2 minutes (M2).
- [ ] AC2 — Cloudflare DNS A-record updated via API (no manual DNS changes).
- [ ] AC3 — DNS TTL set to 60 seconds.
- [ ] AC4 — Old server config backed up as tar archive before migration.
- [ ] AC5 — Health check verifies new server is accepting connections.
- [ ] AC6 — Script outputs rollback instructions on failure.
- [ ] AC7 — `shellcheck scripts/migrate.sh` passes.
- [ ] AC8 — `shellcheck scripts/cloudflare-dns.sh` passes.
- [ ] AC9 — Script outputs post-migration verification command: 'curl -s <health-endpoint> && echo OK' — operator confirms new server accepts proxy connections before old server is decommissioned. Link FQDN unchanged (INV-DOMAIN).

## §7 Constraints

- Requires: ssh access to both old and new servers, Cloudflare API token with DNS edit permission.
- No new dependencies beyond standard Unix tools (tar, scp, curl, jq).

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 architect: patched per RV-ARCH-001 finding L2 (post-migration user-reconnect verification AC added).
- 2026-07-03 opencode-executor: started — implementing scripts/migrate.sh and scripts/cloudflare-dns.sh.
- 2026-07-03 opencode-executor: in_review; tests 0 (bash scripts — no test framework); lint clean (shellcheck pass on both); typecheck N/A (bash).
- 2026-07-03 executor: fix F-H1 (deploy failure masking), F-H2 (dig/seq removal), F-M1 (health check exit)
- 2026-07-03 opencode-orchestrator: merged in 70554b2; RV-CODE-013 verdict=fail→pass (iter 2); F-H3 pre-existing env, Mediums backlogged.
