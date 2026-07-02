---
id: RV-ARCH-NNN
type: arch_review
target_arch: ARCH-NNN@X.Y.Z
prd_ref: PRD-NNN@X.Y.Z
status: in_review     # in_review → done
created: YYYY-MM-DD
---

# RV-ARCH-NNN: review of ARCH-NNN against PRD-NNN

**Verdict:** <pass | pass_with_changes | fail>
**Summary:** <one sentence>

## Goal coverage
| PRD Goal | Component(s) | Covered? |
|---|---|---|
| G1 | C1 | yes |
| G2 | — | NO ← finding |

## Checks
- [ ] Every PRD goal covered by ≥1 component.
- [ ] No component/ADR violates a PRD Non-Goal.
- [ ] §0 Recon Report present and grounded in docs/knowledge/.
- [ ] Every non-trivial decision has a justified ADR; no ADR conflicts.
- [ ] Internally consistent (interfaces agree across sections).
- [ ] All references version-pinned and resolve (validate_docs.py clean).
- [ ] Tickets trace to components; depends_on DAG acyclic; parallel tickets' outputs disjoint.
- [ ] Each goal has an observable acceptance signal in some ticket §6.

## Findings
### High
- <none | …>
### Medium
- <none | …>
### Low
- <none | …>

## Top 3 risks (for the PO's 1-line notice)
1. <…>
2. <…>
3. <…>
