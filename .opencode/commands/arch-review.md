---
description: Audit one ArchSpec against its source PRD before approval. Dispatches the architecture-reviewer subagent (different model family from the Architect) to check goal coverage, Non-Goal compliance, ADR justification, consistency, references, and ticket DAG.
---

You are now running an architecture review.

ArchSpec reference from user: $ARGUMENTS

Load the `arch-review` skill and follow it. Bootstrap (read AGENTS.md, CONTRIBUTING.md,
.opencode/project.jsonc), then dispatch the `architecture-reviewer` subagent on the given
ArchSpec. The reviewer MUST be a different model family than the Architect that authored it.

When it hands back: surface the verdict, uncovered goals, and top 3 risks. Then apply
project.jsonc.autonomy.arch_approval:
- "auto-on-reviewer-pass" + verdict pass  → flip the ArchSpec to approved, send the PO a
  1-line notice with the top risks (unless a decision hits autonomy.always_escalate_on).
- "manual" (or any non-pass verdict)      → present the verdict to the PO; do not approve.

Do not design, do not edit the ArchSpec/ADRs/tickets, do not set status yourself beyond the
delegated auto-approval above.
