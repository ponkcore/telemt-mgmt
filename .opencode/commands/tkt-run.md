---
description: Run a single Ticket end-to-end (executor → reviewer → merge). Escape hatch to drive one TKT outside a full PRD run.
---

You are now orchestrating one TKT cycle.

Ticket reference from user: $ARGUMENTS

Load the `tkt-cycle` skill and follow its workflow exactly. Begin with the bootstrap (read
AGENTS.md, CONTRIBUTING.md, .opencode/project.jsonc, the ticket file in full, every §4 Inputs
reference). Verify upstream gates (status: ready, depends_on done, arch_ref approved) before
dispatching anything.

Delegate code to the `executor` subagent and review to the `reviewer` subagent (different model
family). Use `architect-consult` only for genuine read-only architectural questions.

Do not edit PRDs, ArchSpecs, ADRs, prompts, or repo config. Do not merge before the reviewer
signs off and the project.jsonc checks are green.
