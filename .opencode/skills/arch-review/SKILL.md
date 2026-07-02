---
name: arch-review
description: Use ONLY when auditing one ArchSpec against its source PRD before approval. Covers /arch-review, "review ARCH-003", "audit this architecture before I approve". Dispatches the architecture-reviewer subagent (model family ≠ Architect), then applies the project.jsonc autonomy.arch_approval policy. Do not use for code review (that is tkt-cycle) or for designing.
---

# Skill: Architecture Review

This is the technical-correctness gate that lets the PO step out of rubber-stamping ArchSpecs.
You orchestrate one audit of an ArchSpec against its PRD and then apply the autonomy policy.

## Step 0 — bootstrap

Read `AGENTS.md`, `CONTRIBUTING.md`, `.opencode/project.jsonc` (note `autonomy.arch_approval` and
`autonomy.always_escalate_on`). Locate the ArchSpec: `ls docs/architecture/ARCH-NNN-*.md` (refuse
on zero/multiple). Confirm its source PRD is `status: approved` — if not, stop (upstream gate open).

## Step 1 — dispatch the architecture-reviewer

Delegate to the `architecture-reviewer` subagent. It MUST run on a **different model family** than
the Architect that authored the spec — you route this; if you can't guarantee separation, stop and
tell the PO. Task: audit `ARCH-NNN@X.Y.Z` against its PRD per `docs/reviews/TEMPLATE-arch.md`;
write `docs/reviews/RV-ARCH-NNN-*.md`; hand back verdict + uncovered goals + top-3 risks.

## Step 2 — apply the autonomy policy

On the structured hand-back, surface verdict + uncovered goals + top risks, then:

- **verdict `pass`** and `autonomy.arch_approval == "auto-on-reviewer-pass"** and no risk hits
  `autonomy.always_escalate_on` → flip the ArchSpec `status: draft → approved`, append a
  `revision_log`/note, and send the PO a **1-line notice**: "ARCH-NNN approved (arch-review pass).
  Top risks: <r1>; <r2>; <r3>." Then it is ready for `/prd-run`.
- **verdict `pass` but `arch_approval == "manual"`** → present the verdict + risks; the PO approves
  by hand. Do not approve yourself.
- **verdict `pass_with_changes`** → present the Medium findings; recommend the PO either accept (and
  backlog) or send one iteration back to the external Architect.
- **verdict `fail`** → do NOT approve. Summarise the Highs (uncovered goals, Non-Goal violations,
  broken refs, invalid DAG); recommend an Architect iteration (Mentor can assemble the session).
- **any risk in `always_escalate_on`** → escalate to the PO regardless of verdict/policy.

## Step 3 — report

Tell the PO: verdict, what was approved (if anything), where the RV file is, and the next gate
(`/prd-run PRD-NNN@X.Y.Z` once approved, or an Architect iteration).

## Must NOT

Design or edit the ArchSpec/ADRs/tickets · set `status: approved` outside the delegated
auto-approval above · route the reviewer to the Architect's family · approve while a PRD goal is
uncovered.
