---
name: tkt-cycle
description: Use ONLY when running one Ticket from docs/tickets/TKT-NNN-*.md end-to-end through the pipeline. Covers TKT, ticket cycle, dispatch executor, code review, RV-CODE, merge ticket PR. Triggers on /tkt-run, "run TKT-021", "implement this ticket", "close TKT-NNN". Reads build/test commands from .opencode/project.jsonc — no hardcoded stack. Do not use for PRD or ArchSpec authoring.
---

# Skill: One Ticket Cycle

The orchestration discipline for one TKT cycle, from `status: ready` to merged-and-`done`.
You are the orchestrator. You do not write code — you delegate. All build/test commands come
from `.opencode/project.jsonc.commands`; never hardcode a tool.

## The cycle

```
ready → [1] preflight ─(Q)→ STOP
        [2] executor  ─(blocked)→ Q to PO → STOP
        [3] reviewer
              ├ fail ─────────────→ back to [2] (iter+1, cap 3)
              ├ fail+escalate-arch → architect-consult (see prd-orchestration)
              ├ pass_with_changes ─→ iterate or backlog, then [4]
              └ pass ─────────────→ [4]
        [4] checks gate (project.jsonc.commands) + docs-ci
        [5] merge to main
        [6] close-out: status → done, §10 log
```

## Step 0 — bootstrap (every time)

Read: `AGENTS.md`, `CONTRIBUTING.md`, `.opencode/project.jsonc`, the ticket file in full, every
`§4 Inputs` reference. Verify: (1) ticket `status: ready` (anything else stops unless the user
says "resume"); (2) all `depends_on` tickets `done`; (3) `arch_ref` points to an `approved`
ArchSpec. Any open upstream gate ⇒ stop and tell the user.

## Step 1 — preflight

`git fetch origin && git checkout -b tkt/TKT-NNN-<short-slug> origin/main`. Slug = ticket
file stem minus `TKT-NNN-`. Confirm a clean tree before delegating.

## Step 2 — dispatch executor

Delegate to `executor` with one structured task: ticket file, branch, mandate (implement §5
Outputs + §6 AC, run the `project.jsonc` checks, push, open PR `TKT-NNN: <title>`), the
bootstrap files to read, and the hand-back contract. On hand-back: **Success** → step 3;
**Blocked** (Q-file) → stop, surface the question, do not iterate; **checks red** → re-dispatch
"fix without changing scope", cap 3 iterations.

## Step 3 — dispatch reviewer

The reviewer MUST run on a **different model family** than the executor — you route this. If you
cannot guarantee separation, stop and tell the user. Delegate to `reviewer`: PR branch, ticket,
iteration K, prior RV if K>1, mandate (verdict per `docs/reviews/TEMPLATE-code.md`, commit the RV
on the branch). Wait for the structured hand-back.

## Step 4 — verdict routing

- **fail** → re-dispatch executor ("address findings F-H*/F-M* in the RV; change nothing else"), then re-review. Cap **3 iterations**; still failing ⇒ stop and surface the open Highs.
- **fail + `recommendation: escalate-to-architect`** → do NOT iterate code; auto-call `architect-consult` per the prd-orchestration "Architect-consult auto-call protocol" (works for solo `/tkt-run` too). Outcomes: arch-PR `confidence: high` → merge it, re-dispatch executor on the corrected spec (counts as one iteration); backlog `confidence: medium` → degrade the High to Medium, proceed to step 5 as `pass_with_changes`; `confidence: low` → stop, escalate to PO.
- **pass_with_changes** → if all findings are Medium and stylistic/local, proceed to merge and log each to `docs/backlog/`. If a Medium concerns correctness or a missed AC, iterate once then re-review.
- **pass** → step 5.

## Step 5 — checks gate

Required CI check is `docs-ci` (validates docs frontmatter + refs). Code checks are local — the
executor was responsible for green before push. Verify independently by pulling the PR head and
running the `project.jsonc.commands` (skip any `""`):

```
git fetch origin pull/<N>/head:pr-<N> && git checkout pr-<N>
<commands.install> && <commands.typecheck> && <commands.lint> && <commands.test>
git checkout - && git branch -D pr-<N>
```

Any failure ⇒ verdict `fail`, go to step 4. Never merge a PR you couldn't verify.

## Step 6 — merge

Per `project.jsonc.autonomy.merge`: with `auto-on-reviewer-pass`, merge autonomously when ALL
hold — reviewer `pass` (or `pass_with_changes` with Mediums backlogged/accepted), `docs-ci`
green, local `project.jsonc` checks green. With `manual`, get a PO ack first. Use
`gh pr merge <N> --squash --delete-branch`. No `--admin`, no force-push, only into `main` from a
`tkt/...` branch. After merge: `git checkout main && git pull`; confirm the merge commit; flip
the ticket `status: in_review → done`; append `§10`: `- <ISO-date> opencode-orchestrator: merged
in <SHA>; RV-CODE-NNN verdict=<...>`; commit `TKT-NNN: close cycle` on `main`; push.

## Step 7 — close-out

Tell the user: ticket id+title, merge SHA, iteration count, backlog entries created, and (if in a
PRD walk) the next ready ticket.

## Stop conditions

Executor BLOCKED with a non-localised contradiction (if localised to ArchSpec/ADR text, auto-call
architect-consult instead) · 3 failed review iterations · a finding requiring a file outside every
in-opencode write-zone (PRD wrong, ROADMAP change) · could not verify checks locally.

## Must NOT

Aggregate tickets into one PR · skip an upstream gate · set `status: approved` · invent a Q-file
answer · route reviewer to the executor's family.
