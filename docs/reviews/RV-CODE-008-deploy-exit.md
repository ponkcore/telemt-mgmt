---
id: RV-CODE-008
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/5"
ticket_ref: TKT-008@0.1.1
status: in_review
created: 2026-07-03
---

# RV-CODE-008: review of TKT-008 (PR #5)

**Verdict:** pass_with_changes
**Summary:** All §6 acceptance criteria are met and the diff stays within scope, but three Medium findings around input validation/sanitisation, silent firewall failures, and deploy rollback need to be addressed or backlogged before the next exit-server iteration.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency (uses `ghcr.io/telemt/telemt:latest` and `angie/angie:latest` per §7 Constraints).
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc typecheck/lint green; pytest fails locally due to pre-existing missing `libstdc++.so.6` (greenlet) — reproduced on `main`, not a PR regression.
- [x] project.jsonc invariants hold for the changed deploy artefacts (INV-IDEMPOTENT, INV-DOCKER, INV-SECRETS).

## Acceptance criteria
- AC1 — `deploy-exit.sh:62` calls `load_env "$ENV_FILE"`; `common.sh:32-38` sources existing `.env` and `common.sh:54-59` returns already-set values, so re-runs skip prompts and rewrite config without duplicating containers.
- AC2 — `deploy-exit.sh:67-111` prompts for `DOMAIN`, `AD_TAG`, `TLS_DOMAIN`, `TELEMT_SECRET`, `MANAGEMENT_IPS`, and `MONITORING_IPS`.
- AC3 — `config.toml.template:27,46,48` sets `tls = true`, `mask = true`, `unknown_sni_action = "reject_handshake"`; `:18,22` set `use_middle_proxy = true`, `config_strict = true`.
- AC4 — `docker-compose.yml:29-37` (telemt) and `:54-64` (angie) include `read_only: true`, `security_opt: [no-new-privileges:true]`, `cap_drop: [ALL]`, and `cap_add: [NET_BIND_SERVICE]`.
- AC5 — `angie.conf.template:28-29` and `docker-compose.yml:50` serve the mask host on `:8080` only.
- AC6 — `infra/exit/.env.example:1-32` documents `DOMAIN`, `AD_TAG`, `TLS_DOMAIN`, `TELEMT_SECRET`, `MANAGEMENT_IPS`, `MONITORING_IPS`.
- AC7 — `deploy-exit.sh:175-217` restricts `:9090` to `MONITORING_IPS` and `:9091` to `MANAGEMENT_IPS` via UFW, plus localhost.
- AC8 — `shellcheck infra/exit/deploy-exit.sh` returns no warnings/errors.
- AC9 — `config.toml.template:20` places `ad_tag = "__AD_TAG__"` under `[general]`.
- AC10 — `config.toml.template:18` sets `use_middle_proxy = true`.
- AC11 — `deploy-exit.sh:240-242` prints the required post-deploy `@MTProxybot /myproxies` message.
- AC12 — `deploy-exit.sh:22-32` implements a `_finish_timer` EXIT trap that prints elapsed seconds.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- F-M1: `deploy-exit.sh:155-161` substitutes user inputs (`AD_TAG`, `TLS_DOMAIN`, `AUTH_HEADER`, etc.) into `sed` replacement text without validation or escaping. Characters such as `|`, `&`, or `\` in operator input can corrupt `config.toml` or alter the replacement.
- F-M2: `deploy-exit.sh:175-217` swallows UFW/sudo failures with `2>/dev/null || true`; invalid IPs or permission problems silently leave firewall rules incomplete.
- F-M3: `deploy-exit.sh:223-229` runs `docker compose down` before `up -d` with no rollback path; if `up` fails, the exit server is left down.

### Low  (optional)
- F-L1: `infra/exit/.env.example` does not document the auto-generated `AUTH_HEADER` variable that `deploy-exit.sh:124` writes to `.env`.
- F-L2: `docs/tickets/TKT-008-deploy-exit.md:5` still cites `arch_ref: ARCH-001@0.1.1`, while the approved spec is `ARCH-001@0.1.2`; update on the next ticket revision.

## Red-team probes  (one line each; N/A allowed)
- error_paths: UFW/sudo and `docker compose` errors are partly masked by `|| true`; a failed `docker compose up` does stop the script due to `set -e`, but UFW misconfigurations are silent.
- concurrency: N/A — single-threaded interactive deploy script.
- input_validation: Operator inputs (`DOMAIN`, `AD_TAG`, `TLS_DOMAIN`, IP lists) are not validated, so malformed values can break `sed` substitution or UFW rules.
- prompt_injection: User-supplied values reach `sed` replacement strings and UFW `allow from` arguments; special characters can corrupt the generated `config.toml` or firewall rules.
- authz_isolation: `:9090` and `:9091` are restricted to the specified monitoring/management IPs plus localhost, consistent with ARCH-001@0.1.2 §9 Threat Surfaces.
- secrets: `TELEMT_SECRET` and `AUTH_HEADER` are generated/stored in `.env` (gitignored) and written to the generated `config.toml` on the server; no secrets are committed in this diff.
- observability: The script prints progress and elapsed time, but does not persist logs or add container healthchecks.
- rollback: No rollback on failure; `docker compose down` followed by `up` means a failed `up` leaves the service down (F-M3).
- dns_failover: N/A — single-domain exit server; failover is out of scope for this ticket.
