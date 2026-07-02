---
id: TKT-NNN
type: ticket
status: draft        # draft → ready → in_progress → in_review → done | blocked
arch_ref: ARCH-NNN@X.Y.Z
depends_on: []       # e.g. [TKT-001@X.Y.Z, TKT-002@X.Y.Z]
estimate: M          # S | M | L
created: YYYY-MM-DD
---

# TKT-NNN: <Title>

## §1 Goal
<One sentence. What shippable change this ticket delivers.>

## §2 In Scope
- <…>

## §3 NOT In Scope  *(mandatory — at least one)*
- <…>   (the reviewer fails the PR if the diff touches any of these)

## §4 Inputs
<The ONLY sources of design intent. Pin every reference.>
- ARCH-NNN@X.Y.Z §<n>
- ADR-NNN@X.Y.Z

## §5 Outputs
<Exact file list the executor's diff must match. Keep disjoint from sibling tickets so
they can run in parallel.>
- `src/...`
- `tests/...`

## §6 Acceptance Criteria
<Machine-checkable. Each becomes a file:line or a passing test in review.>
- [ ] AC1 — <…>
- [ ] AC2 — <…>

## §7 Constraints
- <hard rules; list any authorised new dependency here, else none allowed>

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
<Append-only, one line per transition. The orchestrator/executor write here.>
- YYYY-MM-DD <agent>: <note>
