---
id: RV-CODE-016
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/16"
ticket_ref: TKT-016@0.2.0
status: in_review
created: 2026-07-04
---

# RV-CODE-016: review of TKT-016@0.2.0 — Angie SNI Routing Template for Shared Exit Servers (PR #16)

**Verdict:** pass
**Summary:** The PR delivers the optional Angie SNI routing template and README documentation; all ACs are met, no High/Medium findings, and the Angie config validates successfully with `angie -t`.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `infra/exit/angie-sni-router.conf.template:57` contains `stream { … }` block and line 71 contains `ssl_preread on;`
- AC2 — `infra/exit/angie-sni-router.conf.template:62` uses `__TELEMT_SNI__` placeholder for the telemt service SNI
- AC3 — `infra/exit/angie-sni-router.conf.template:64` maps `default` to `127.0.0.1:8443` (telemt backend)
- AC4 — `infra/exit/angie-sni-router.conf.template:84` opens an `http` block with `listen 8080;` for the mask host
- AC5 — `README.md:110-162` documents standalone vs shared deployment modes with the comparison table at lines 119-129
- AC6 — `angie -t` run via the official Angie Docker image (`docker.angie.software/angie:latest`) reports: "configuration file /etc/angie/angie.conf test is successful"

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- none

### Low  (optional)
- none

## Red-team probes
- error_paths: N/A — stream `default` route falls back to telemt; no error-handling logic beyond Angie's built-in TCP proxy.
- concurrency: N/A — template is declarative; no application-level concurrency.
- input_validation: N/A — SNI is parsed by Angie's `ssl_preread` from the TLS ClientHello; no user input is processed.
- prompt_injection: N/A — no LLM prompts in this change.
- authz_isolation: Shared mode keeps telemt on internal port 8443 and only Angie exposes 443, matching the defense-in-depth intent of ADR-008@0.2.0.
- secrets: No secrets in the template; only `__TELEMT_SNI__` placeholder and local backend addresses.
- observability: N/A — no metrics/logging added or removed.
- rollback: N/A — rollback is operator-driven by reverting to `angie.conf.template`.
- dns_failover: N/A — DNS handling is unchanged.
