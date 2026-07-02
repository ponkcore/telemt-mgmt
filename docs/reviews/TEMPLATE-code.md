---
id: RV-CODE-NNN
type: code_review
target_pr: "<PR URL>"
ticket_ref: TKT-NNN@X.Y.Z
status: in_review     # in_review → done
created: YYYY-MM-DD
---

# RV-CODE-NNN: review of TKT-NNN (PR #<N>)

**Verdict:** <pass | pass_with_changes | fail>
**Summary:** <one sentence>

## Contract compliance
- [ ] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [ ] No §3 NOT-In-Scope term touched.
- [ ] No unauthorised runtime dependency.
- [ ] Every §6 AC verifiably met (citations below).
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — <file:line | test name>
- AC2 — <…>

## Findings
### High  (block merge)
- <none | F-H1: file:line — issue>
### Medium  (fix or backlog)
- <none | F-M1: …>
### Low  (optional)
- <none | F-L1: …>

## Red-team probes  (one line each; N/A allowed)
- error_paths: <…>
- concurrency: <…>
- input_validation: <…>
- prompt_injection: <…>
- authz_isolation: <…>
- secrets: <…>
- observability: <…>
- rollback: <…>
