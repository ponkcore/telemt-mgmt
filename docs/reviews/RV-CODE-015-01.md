---
id: RV-CODE-015-01
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/18"
ticket_ref: TKT-015@0.2.0
status: in_review
created: 2026-07-04
---

# RV-CODE-015-01: review of TKT-015@0.2.0 (PR #18)

**Verdict:** pass
**Summary:** The PR correctly switches the entry→exit PROXY protocol to v1, fixes the redirect port to `:443`, and adds the required PROXY protocol / TLS emulation settings to the exit template; all acceptance criteria are met and all checks pass.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `infra/entry/xray-config.json.template:57`: `"proxyProtocol": 1`
- AC2 — `infra/entry/xray-config.json.template:56`: `"redirect": "__EXIT_SERVER_IP__:443"`
- AC3 — `infra/exit/config.toml.template:32`: `proxy_protocol = true`
- AC4 — `infra/exit/config.toml.template:53`: `mask_proxy_protocol = 1`
- AC5 — `infra/exit/config.toml.template:55`: `tls_emulation = true`
- AC6 — Verified: placeholder-substituted entry template passes `jq .`
- AC7 — Verified: placeholder-substituted exit template parses with `tomllib.loads`

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- none

### Low  (optional)
- F-L1: `infra/exit/config.toml.template:30-55` — consider adding a brief inline note that `mask_proxy_protocol = 1` must match the entry server's `proxyProtocol` value to avoid silent mismatches. This is already implied by the architecture but an explicit cross-reference could help operators. (cosmetic, backlog)

## Red-team probes  (one line each; N/A allowed)
- error_paths: N/A — template only, no executable error paths added.
- concurrency: N/A — no concurrent code changed.
- input_validation: N/A — templates remain placeholder-driven; no input parsing added.
- prompt_injection: N/A — no LLM/prompt surfaces involved.
- authz_isolation: N/A — no authz changes.
- secrets: No secrets committed; placeholders (`__...__`) and `.env` flow unchanged.
- observability: N/A — Prometheus/metrics config untouched.
- rollback: N/A — deploy scripts unchanged; idempotency preserved.
