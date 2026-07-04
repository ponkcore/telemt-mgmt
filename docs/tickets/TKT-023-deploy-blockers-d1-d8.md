---
id: TKT-023
type: ticket
status: in_review
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: L
created: 2026-07-04
---

# TKT-023: Deploy blockers — D1-D8 from test deployment

## §1 Goal
Fix all 8 deploy blockers discovered during the 2026-07-04 test deployment (`docs/knowledge/TELEMT_DEPLOY_REPORT_2026-07-04.md`), making `docker compose up` succeed on both entry and exit servers without manual workarounds.

## §2 In Scope

| # | Issue | Fix |
|---|-------|-----|
| D1 | `angie/angie:latest` image doesn't exist | Replace with `docker.angie.software/angie:1.8.1-alpine` (official Angie registry) in all compose files |
| D2 | Xray config mount path wrong (`/etc/xray/` → `/usr/local/etc/xray/`) | Fix volume mount in entry + exit compose files |
| D3 | telemt config.toml not loaded (wrong working dir) | Add `command: ["/etc/telemt/config.toml"]` to telemt service |
| D4 | `config_strict=true` rejects `access.user_data_quota_bytes` | Remove `[access.user_data_quota_bytes]` section from `config.toml.template` |
| D5 | `cap_drop: ALL` breaks :443 bind + Angie chown | Per-service cap fixes (see details below) |
| D6 | `INFRA_DIR` path bug (`../..` → `..`) | Fix in `deploy-exit.sh`, `deploy-mgmt.sh`, `deploy-monitoring.sh`, `deploy-landing.sh` (entry is TKT-020@0.2.1) |
| D7 | `xray x25519` / `xray uuid` double command | Remove extra `xray` prefix in `deploy-exit.sh` (entry is TKT-020@0.2.1) |
| D8 | `tls_emulation` mask_host/port logic wrong | In third-party mode, set `mask_port = 443` (fetches from real domain) instead of 8080. Update `deploy-exit.sh` and `config.toml.template` comments. Add `proxy_protocol_trusted_cidrs = ["127.0.0.1/32"]` to config template. |

### D5 per-service cap fix detail

**Xray (entry + exit):**
```yaml
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE]
user: "0:0"  # root required for port 443 binding with cap_add
```

**Angie (exit, mgmt, landing):**
```yaml
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE, CHOWN, SETGID, SETUID]
# Remove read_only: true — Angie needs to write to cache dirs
```

**telemt:**
```yaml
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE]
# read_only: true — keep (telemt only writes to mounted volumes)
```

## §3 NOT In Scope
- `infra/entry/xray-config.json.template` — owned by TKT-020@0.2.1.
- `infra/entry/deploy-entry.sh` — owned by TKT-020@0.2.1 (includes D6/D7 for entry).
- `infra/exit/xray-config.json.template` — owned by TKT-020@0.2.1 (xver fix).
- Code files (api/, telemt_proxy/, bot/) — owned by TKT-021@0.2.1.
- `.env.example` files — owned by TKT-022@0.2.1.
- `scripts/migrate.sh` — owned by TKT-022@0.2.1.

## §4 Inputs
- `docs/knowledge/TELEMT_DEPLOY_REPORT_2026-07-04.md` — issues 7.1-7.10
- ARCH-001@0.2.1 §5 INV-DOCKER (hardening invariant)
- ADR-009@0.2.1 (telemt on :8443, Xray on :443)
- GitHub issues #30-#37 (deploy blockers)

## §5 Outputs
- `infra/entry/docker-compose.yml` — D2 (mount path), D5 (caps/user)
- `infra/exit/docker-compose.yml` — D1 (Angie image), D2 (mount path), D3 (telemt command), D5 (caps/user for all 3 services)
- `infra/exit/config.toml.template` — D4 (remove unsupported key), D8 (mask_port comment, add proxy_protocol_trusted_cidrs)
- `infra/exit/deploy-exit.sh` — D6 (INFRA_DIR), D7 (xray command), D8 (mask_port=443 in third-party mode)
- `infra/mgmt/docker-compose.yml` — D1 (Angie image), D5 (caps)
- `infra/mgmt/deploy-mgmt.sh` — D6 (INFRA_DIR)
- `infra/monitoring/deploy-monitoring.sh` — D6 (INFRA_DIR)
- `infra/landing/docker-compose.yml` — D1 (Angie image), D5 (caps)
- `infra/landing/deploy-landing.sh` — D6 (INFRA_DIR)

## §6 Acceptance Criteria
- [ ] AC1 — No compose file references `angie/angie:latest`. All use a verified working image.
- [ ] AC2 — Xray config volume mounts to `/usr/local/etc/xray/config.json:ro` in both entry and exit compose files.
- [ ] AC3 — telemt service in exit compose has `command: ["/etc/telemt/config.toml"]`.
- [ ] AC4 — `config.toml.template` does not contain `access.user_data_quota_bytes`. `config_strict = true` is preserved.
- [ ] AC5 — Xray services have `user: "0:0"`. Angie services have `cap_add: [NET_BIND_SERVICE, CHOWN, SETGID, SETUID]` and no `read_only: true`.
- [ ] AC6 — All deploy scripts (except entry, owned by TKT-020@0.2.1) have `INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"` (one level up, not two).
- [ ] AC7 — `deploy-exit.sh` xray key generation uses `x25519` / `uuid` without extra `xray` prefix.
- [ ] AC8 — In third-party mode, `MASK_PORT=443` (not 8080). Config template comments updated.
- [ ] AC9 — `config.toml.template` includes `proxy_protocol_trusted_cidrs = ["127.0.0.1/32"]` in `[server]` section.
- [ ] AC10 — `docker compose up -d` succeeds on a clean Ubuntu server for both entry and exit roles (verified by manual config inspection — no live test required in this ticket).

## §7 Constraints
- No new dependencies.
- Angie image must be from an official or well-maintained source. Verify the image exists before committing (docker pull test or registry check). Options: `docker.angie.software/angie:1.8.1-alpine` (official Angie registry) or `socheatsok78/angie:1.11.7-ubuntu` (community, verified working in deploy report).
- INV-DOCKER hardening must be preserved: `cap_drop: ALL`, `security_opt: no-new-privileges`, `read_only` where feasible.

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
- 2026-07-04 opencode-executor: started; implementing §5 Outputs (D1-D8 deploy blockers).
- 2026-07-04 opencode-executor: in_review; ruff pass, pytest 198 pass (1 skip), shellcheck clean, validate_docs 1 pre-existing error (RV-CODE-022-01, not in scope), AC1-AC10 all verified.
