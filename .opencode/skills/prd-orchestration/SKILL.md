---
name: prd-orchestration
description: Use ONLY when running every Ticket of one PRD end-to-end through opencode. Covers /prd-run, "run PRD-003", "process this PRD", "ship all tickets for PRD-NNN". Walks the depends_on DAG topologically, parallelises independent tickets up to project.jsonc concurrency_cap, dispatches one ticket cycle each (per tkt-cycle), escalates to PO on substantive blockers. Do not use for PRD/ArchSpec authoring.
---

# Skill: One PRD Orchestration

The long-running outer loop. The PO gave you a PRD id (e.g. `PRD-003@0.1.3`); you autonomously
close every Ticket tracing to it, walking the `depends_on` DAG and **parallelising independent
work by default** (per CONTRIBUTING.md and `.opencode/project.jsonc.orchestration`). This is a
multi-hour run — be patient and disciplined.

## Step 0 — bootstrap & gates

Re-read: `AGENTS.md`, `CONTRIBUTING.md`, `.opencode/project.jsonc`; the PRD in full (must be
`status: approved`, else refuse); the referenced ArchSpec (must be `approved`); every ADR cited
(gating ones `accepted`); the Tickets the ArchSpec lists. Any open upstream gate ⇒ stop, name it,
don't proceed. Locate the PRD: `ls docs/prd/PRD-NNN-*.md` (refuse on zero/multiple).

## Step 1 — build the DAG

Parse each ticket's frontmatter (`id`, `status`, `depends_on`, `blocks`). Build edges from each
`depends_on` to the ticket; verify acyclic (a cycle is a hard stop — escalate). Per ticket compute:
`ready_now` (all `depends_on` are `done` AND status is `ready`/`blocked`), `done`, `in_flight`
(`in_progress`/`in_review` — recovering a crashed run is fine).

## Step 2 — initial report, then "go"

One-screen summary: PRD id/title/version; ArchSpec id/version; ticket tally (total/done/in_flight/
ready_now/blocked-dep/blocked-Q); topological order; **the parallelism windows** (sets of tickets
with disjoint `§5 Outputs` and no mutual transitive dependency that you will run concurrently);
concurrency cap in force; and the line "I will run autonomously, pausing only on [stop conditions].
Reply 'go' to start." Wait for "go".

## Step 3 — main loop (parallel by default)

State: `frontier` (ready_now), `in_flight`, `done`, `blocked`. Read
`project.jsonc.orchestration`: `parallelism` (`auto`|`sequential`) and `concurrency_cap` (default 3).

While `frontier ∪ in_flight ≠ ∅`:
1. **Fill the parallel slots.** While `parallelism == "auto"` AND `|in_flight| < concurrency_cap`
   AND `frontier` has an admissible ticket, dispatch it. A ticket is admissible to run alongside
   the current `in_flight` set iff: its `§5 Outputs` paths are **disjoint** from every in-flight
   ticket's outputs, AND it shares no transitive `depends_on` relationship with any of them. If
   `parallelism == "sequential"`, keep `concurrency_cap` effectively 1.
   Selection order: smallest `estimate` first (S<M<L), ties by id ascending.
2. Move each dispatched ticket `frontier → in_flight`; run it via the `tkt-cycle` skill
   (concurrent cycles each keep the reviewer family ≠ executor family rule).
3. On a cycle return:
   - **Merged** → `done`. Re-scan the DAG: tickets whose `depends_on` is now fully `done` join `frontier`.
   - **Blocked (Q-file)** → `blocked`; notify the PO with the Q-path; keep other slots running.
   - **Aborted** (3 review fails / checks red repeatedly) → `blocked`; notify; continue other slots only if the PO said "continue on partial failure", else stop the loop and report.
4. If `frontier` is empty but `in_flight` non-empty: wait for a slot to free.
5. Both empty and `blocked` non-empty: stop, report.

Be transparent: print state at every transition ("TKT-021 done; in_flight {TKT-022, TKT-026}; frontier {TKT-030}").

## Step 4 — close-out report

Tickets `done` (count+list) · tickets `blocked` (with reason) · new backlog entries · new questions ·
total runtime · a one-line gate-check on the PRD `§2 Goals` (which appear satisfied by merged
tickets, which remain).

## Architect-consult auto-call protocol

When a TKT cycle hands back reviewer `fail` + `recommendation: escalate-to-architect`, OR an
executor returns BLOCKED with a Q-file citing a design-artefact contradiction, do NOT escalate to
PO yet:
1. Halt only the failing cycle; keep the rest of the frontier running.
2. Dispatch `architect-consult` with: the triggering RV/Q-file path, the ticket id + PR/branch, the
   specific blocking finding, and a one-paragraph read of why it looks localised to ArchSpec/ADR.
3. Wait for its structured hand-back:
   - **edited ArchSpec/new ADR + arch PR, `confidence: high`, `merge-arch-pr-then-iterate-ticket`** → review the arch PR (CI green, validator clean), squash-merge to `main`, sync `main`, re-dispatch the failing ticket (executor rebases, addresses the corrected findings).
   - **backlog only, `confidence: medium`, `accept-with-backlog`** → mark the ticket PR `pass_with_changes` (the High becomes Medium — spec was the issue), backlog the deeper change, merge, continue.
   - **no edit, `confidence: low`, `pause-and-escalate-to-po`** → stop the walk, report to the PO with the hand-back + RV + PR.
4. Cap: a single TKT cycle gets ≤ **2** architect-consult calls; a second `confidence: low` (or two failed arch PRs) ⇒ stop and escalate to PO.

architect-consult write-rights: `docs/architecture/**` (patch fixes + new ADRs only), `docs/backlog/**`,
`docs/questions/**`. It never touches code/tickets/PRDs/ROADMAP/prompts/knowledge/repo config. The
external Architect (PO-curated) remains the only authority for new components, new PRDs, or whole
ArchSpec rewrites.

## Stop conditions (escalate; do not auto-resolve)

DAG cycle · upstream gate open · a ticket's `§4 Inputs` references a non-existent artefact · two
in-flight tickets' `§5 Outputs` overlap (shouldn't happen if the architect did their job — check) ·
a verdict needs a file outside every in-opencode write-zone · architect-consult returns
`confidence: low` · more than 3 tickets `blocked` (systemic) · any decision hitting
`project.jsonc.autonomy.always_escalate_on`.

## Must NOT

Author/edit PRD/ArchSpec/ADR/Tickets · skip an upstream gate · aggregate tickets into one PR · skip
or add a ticket · change a ticket's `depends_on` · run >1 PRD orchestration in one session ·
invent a Q-file answer.
