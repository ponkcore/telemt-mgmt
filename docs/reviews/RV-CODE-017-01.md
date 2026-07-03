---
id: RV-CODE-017-01
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/20"
ticket_ref: TKT-017@0.2.0
status: in_review
created: 2026-07-04
---

# RV-CODE-017-01: review of TKT-017@0.2.0 (PR #20)

**Verdict:** pass  
**Summary:** The PR adds the required Russian datacenter provider guidance banner to `deploy-entry.sh` and a matching README section with a Signal-1 comparison table, without touching any NOT-In-Scope items or functional logic.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (`infra/entry/deploy-entry.sh`, `README.md`) plus the ticket's own `status` and `§10` log.
- [x] No §3 NOT-In-Scope term touched (no automated provider detection, no IP-to-ASN lookup, no exit server provider guidance, no functional logic changes).
- [x] No new runtime dependency introduced.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (`ruff`, `pytest`, `mypy`, `tsc`, `validate_docs.py`, `shellcheck`).
- [x] All project.jsonc invariants hold; text-only change does not affect invariants.

## Acceptance criteria
- AC1 — `deploy-entry.sh` displays provider guidance before prompts  
  `infra/entry/deploy-entry.sh:67-83` (banner printed before `load_env` and configuration prompts at `:85`).
- AC2 — Beget, TimeWeb, reg.ru explicitly recommended  
  `infra/entry/deploy-entry.sh:70-73`; `README.md:122-126`.
- AC3 — Selectel, Yandex.Cloud explicitly warned as Signal-1 flagged  
  `infra/entry/deploy-entry.sh:75-77`; `README.md:127-128`.
- AC4 — README.md contains a provider comparison table with Signal 1 status  
  `README.md:120-128`.
- AC5 — Documentation references TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 and §6  
  `README.md:139-140`; `infra/entry/deploy-entry.sh:81`.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- none

### Low  (optional)
- none

## Red-team probes
- error_paths: N/A — change is static text only; no error-handling paths modified.
- concurrency: N/A — no concurrent code or threading changes.
- input_validation: N/A — no new user input handling added.
- authz_isolation: N/A — no auth or isolation boundaries affected.
- secrets: N/A — no secrets or env handling introduced.
- observability: N/A — no metrics, logs, or tracing changes.
- rollback: N/A — deploy script functional logic is unchanged; rollback behavior unaffected.
- dns_failover: N/A — no DNS or failover logic added.
