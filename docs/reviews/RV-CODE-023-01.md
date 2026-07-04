---
id: RV-CODE-023-01
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/41"
ticket_ref: TKT-023@0.2.1
status: in_review
created: 2026-07-04
---

# RV-CODE-023-01: review of TKT-023 (PR #41)

**Verdict:** pass_with_changes
**Summary:** All 10 §6 acceptance criteria are met and shell/Python checks pass, but `docs-ci` fails on two pre-existing unversioned ticket references in `docs/reviews/` that are already fixed on `main`.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `docker.angie.software/angie:1.8.1-alpine` is used in `infra/exit/docker-compose.yml:77`, `infra/mgmt/docker-compose.yml:42`, and `infra/landing/docker-compose.yml:16`; no compose file retains `angie/angie:latest` as an image reference.
- AC2 — Xray config mount is `/usr/local/etc/xray/config.json:ro` in `infra/entry/docker-compose.yml:37` and `infra/exit/docker-compose.yml:56`.
- AC3 — `telemt` service in `infra/exit/docker-compose.yml:28` has `command: ["/etc/telemt/config.toml"]`.
- AC4 — `infra/exit/config.toml.template:38` preserves `config_strict = true`; the removed `[access.user_data_quota_bytes]` block is absent.
- AC5 — Xray services have `user: "0:0"` in `infra/entry/docker-compose.yml:27` and `infra/exit/docker-compose.yml:58`; Angie services add `CHOWN`, `SETGID`, `SETUID` to `NET_BIND_SERVICE` in `infra/exit/docker-compose.yml:95-98`, `infra/mgmt/docker-compose.yml:68-71`, and `infra/landing/docker-compose.yml:36-40`; `read_only: true` is removed from Angie services and kept on `telemt` in `infra/exit/docker-compose.yml:35`.
- AC6 — All non-entry deploy scripts use `INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"`: `infra/exit/deploy-exit.sh:62`, `infra/monitoring/deploy-monitoring.sh:31`, `infra/landing/deploy-landing.sh:18`; `infra/mgmt/deploy-mgmt.sh:32` already had the correct value (unchanged in this PR).
- AC7 — `infra/exit/deploy-exit.sh:343` uses `docker run ... x25519` and `:387` uses `docker run ... uuid` without the extra `xray` subcommand.
- AC8 — `infra/exit/deploy-exit.sh:274` sets `MASK_PORT=443` for third-party mode; `infra/exit/config.toml.template:12,26-29,75-76` comments are updated to reflect `443`.
- AC9 — `infra/exit/config.toml.template:51` adds `proxy_protocol_trusted_cidrs = ["127.0.0.1/32"]` in the `[server]` section.
- AC10 — No live deployment test is required by the ticket; compose file inspection confirms the blockers addressed.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- F-M1: `python3 scripts/validate_docs.py` fails on pre-existing unversioned references in `docs/reviews/RV-CODE-020-01.md` (`TKT-020`) and `docs/reviews/RV-CODE-022-01.md` (`TKT-022`). These files are not in this PR diff and are already fixed on `main`; the branch must be rebased/merged with `main` before `docs-ci` can be green. The executor's §10 log undercounts this as one error.

### Low  (optional)
- none

## Red-team probes  (one line each; N/A allowed)
- error_paths: Docker fallback for `x25519`/`uuid` generation in `deploy-exit.sh` is graceful; no new failure modes introduced.
- concurrency: N/A — no concurrency changes.
- input_validation: N/A — deploy script inputs continue to be handled by existing `infra/lib/common.sh` helpers.
- prompt_injection: N/A — no LLM/prompt paths.
- authz_isolation: N/A — no authz changes.
- secrets: No secrets added to compose files; `.env` and `env_file` usage preserved (INV-SECRETS).
- observability: N/A — logging/metrics/healthcheck configuration unchanged.
- rollback: N/A — existing idempotency and rollback paths unchanged.
- dns_failover: N/A — no DNS logic changes.
