---
id: BACKLOG-001
type: backlog
status: wontfix
source: RV-ARCH-001-v2@0.1.1
created: 2026-07-02
---

# BACKLOG-001: TKT-005@0.1.0 §7 slowapi dependency contradiction

## What

TKT-005@0.1.0 §7 Constraints states "No new dependencies beyond TKT-001@0.1.1" but then
suggests "use `slowapi` or custom middleware (add `slowapi` to dev deps if needed)." Adding
`slowapi` would be a new dependency, contradicting the first sentence. The executor will
choose custom middleware (Option B below) to avoid the contradiction.

## Why deferred

This is a Low finding (RV-ARCH-001-v2). It does not block ArchSpec approval or ticket execution.
The executor will either use `slowapi` (and add it to TKT-001@0.1.1 deps) or implement custom
middleware (no new dep). The contradiction is in the ticket constraint text, not in the
architecture. Neither the Mentor nor architect-consult can edit tickets — this requires the
external Architect or PO.

## Suggested resolution

When the external Architect or PO next touches TKT-005@0.1.0, change §7 to one of:
- **Option A:** "Rate limiting via `slowapi` (added to TKT-001@0.1.1 dev dependencies)." — authorise the dep.
- **Option B:** "Rate limiting via custom FastAPI middleware (no new dependencies)." — remove the slowapi option.

Option B is simpler and avoids a new dep. The custom middleware is ~20 lines (in-memory IP
counter with TTL). Recommend Option B.

## Resolution

Closed as wontfix (TKT-026@0.1.0). The executor chose custom middleware (Option B) —
no slowapi dependency was added. The contradiction in TKT-005@0.1.0 §7 is
moot since no slowapi was used. The ticket text is historical and cannot be
edited by the Mentor or architect-consult.
