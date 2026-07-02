---
description: Run all Tickets of one PRD end-to-end, walking depends_on topologically, parallelising independent tickets up to project.jsonc concurrency_cap, dispatching executor + reviewer per ticket. Pauses only on substantive blockers.
---

You are now orchestrating an entire PRD run.

PRD reference from user: $ARGUMENTS

Load the `prd-orchestration` skill and follow its workflow exactly. Begin with the bootstrap
(read AGENTS.md, CONTRIBUTING.md, .opencode/project.jsonc, the PRD file, the ArchSpec it
references, the ADRs, and the ticket set), produce the initial state report (including the
parallelism windows you will use), and wait for the user's "go" before dispatching anything.

When dispatching individual ticket cycles, use the `tkt-cycle` skill for each one. Parallelise
independent tickets per CONTRIBUTING.md "Parallelism" and project.jsonc.orchestration.

Delegate code to the `executor` subagent, code review to the `reviewer` subagent (different
model family), and architectural questions (sparingly) to `architect-consult`.

Do not edit PRDs, ArchSpecs, ADRs, prompts, or repo-wide config. Do not merge before the
reviewer signs off and the project.jsonc checks are green.
