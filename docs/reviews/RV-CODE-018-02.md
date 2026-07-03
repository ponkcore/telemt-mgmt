---
id: RV-CODE-018-02
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/19"
ticket_ref: TKT-018@0.2.0
status: in_review
created: 2026-07-04
---

# RV-CODE-018-02: review of TKT-018@0.2.0 (PR #19)

**Verdict:** pass
**Summary:** F-H1 and F-M1 from RV-CODE-018-01 are resolved, all 15 acceptance criteria are met, and project checks are green.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `infra/entry/xray-config.json.template:30` `"xver": 1`
- AC2 — `infra/entry/xray-config.json.template:53` `"protocol": "vless"`
- AC3 — `infra/entry/xray-config.json.template:63` `"flow": "xtls-rprx-vision"`; line 71 `"security": "reality"`
- AC4 — `infra/exit/xray-config.json.template:12` VLESS-Reality inbound on port 443
- AC5 — `infra/exit/xray-config.json.template:56` `"redirect": "127.0.0.1:8443"`; no `proxyProtocol` field
- AC6 — `infra/exit/docker-compose.yml:45-66` `xray-exit` service with `cap_drop: [ALL]`, `read_only: true`, `security_opt: [no-new-privileges:true]`, `cap_add: [NET_BIND_SERVICE]`
- AC7 — `infra/exit/docker-compose.yml:25,49,72` all services use `network_mode: host`
- AC8 — `infra/exit/config.toml.template:30` `port = 8443`
- AC9 — `infra/exit/deploy-exit.sh:146-185` generates X25519 keypair for exit Xray
- AC10 — `infra/exit/deploy-exit.sh:189-218` generates VLESS UUID for exit Xray
- AC11 — `infra/entry/deploy-entry.sh:84-103` prompts for `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`
- AC12 — `infra/entry/xray-config.json.template:30` entry inbound `xver:1`; `infra/exit/xray-config.json.template:30` exit inbound `xver:1`; `infra/exit/config.toml.template:32` `proxy_protocol = true`; PROXYv1 chain preserved
- AC13 — Verified by substituting placeholders and running `jq .` on both generated configs (entry and exit templates)
- AC14 — `infra/exit/deploy-exit.sh:79,99,147,189,223,233` loads existing `.env` and skips generation when values exist
- AC15 — `infra/exit/deploy-exit.sh:218,184-185,257` stores `EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_SHORT_IDS` in `.env`

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- none

### Low  (optional)
- none

## Red-team probes  (one line each; N/A allowed)
- error_paths: `deploy-entry.sh` and `deploy-exit.sh` use `set -euo pipefail` and validate required inputs before use.
- concurrency: N/A — deploy scripts are single-threaded; no shared mutable state beyond `.env` writes during sequential prompts.
- input_validation: Prompted values are written to `.env` unvalidated (UUID/key format), but the operator copies them from `deploy-exit.sh` output, so integrity is preserved by the generation step.
- prompt_injection: N/A — no LLM prompts in this code change.
- authz_isolation: VLESS UUID and Reality keys are scope-specific to the entry↔exit tunnel; telemt API auth_header remains separate.
- secrets: New secrets (`EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_SHORT_IDS`) are stored in `.env` and not committed (INV-SECRETS).
- observability: N/A — no new logging/telemetry; Xray logs go to stdout via Docker.
- rollback: Re-running `deploy-exit.sh`/`deploy-entry.sh` reads `.env` and regenerates configs, enabling quick rollback by reverting `.env` and re-running.
- dns_failover: N/A — out of scope for this ticket.

## Previous review status
- **F-H1 (High):** RESOLVED — `infra/exit/xray-config.json.template:30` now has `"xver": 1`.
- **F-M1 (Medium):** RESOLVED — `docs/tickets/TKT-018-encrypted-s2-vless-reality.md:4` now shows `status: in_review`.
