# Contributing — Process Rules

How the four roles collaborate. Not suggestions: CI enforces the machine-checkable
parts (`scripts/validate_docs.py`), the reviewer subagents enforce the rest, the PO is
final authority. All stack-specific values (commands, conventions, invariants) come
from `.opencode/project.jsonc` — never hardcode them here or in agent prompts.

`.opencode/project.jsonc` is **generated, not hand-authored**: created via the
`/project-setup` genesis prompt and then kept maintained by the Mentor, which syncs the
Architect's cross-cutting invariants (ArchSpec §5) into it on ingest. The PO approves
changes to it; the Mentor owns the edits.

## Roles and write-zones

| Role | MAY write | MUST NOT write |
|---|---|---|
| Product Owner | Anything (final authority) | — |
| Mentor | `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `opencode.json`, `.opencode/**`, `docs/backlog/`, `docs/questions/`, `docs/drafts/`, `.gitignore` | code zones, `docs/prd|architecture|tickets|reviews|roadmap|prompts|knowledge/`, `.github/`, `infra/`, `scripts/`, build/dep files, secrets. **NEVER `status: approved`.** |
| Business Planner | `docs/prd/`, `docs/roadmap/` (with PO authorisation) | `docs/architecture/`, `docs/tickets/`, code, everything else |
| Technical Architect | `docs/architecture/`, `docs/tickets/` | `docs/prd/`, `docs/roadmap/`, code, `infra/`, repo root |
| Sisyphus | ticket frontmatter promotion only (`status`, `§10 Execution Log`), backlog, questions. Delegates code→executor, review→reviewer/architecture-reviewer. | PRD/ArchSpec/ADR bodies, prompts, knowledge, repo config, `.github/`, `infra/`, `scripts/` |
| executor | code zones (`project.jsonc.conventions.code_write_zones`), files in the assigned ticket's `§5 Outputs`, own ticket `status` (transitions only) + `§10 Execution Log` (append-only) | all other ticket fields, all other docs zones, repo config, other tickets |
| reviewer | `docs/reviews/` only | everything else. **NEVER `status: approved`.** |
| architect-consult | `docs/architecture/**` (patch fixes + NEW ADRs only — no minor/major bumps, no component removal, no ADR retirement), `docs/backlog/**`, `docs/questions/**` | code, tickets, PRDs, ROADMAP, prompts, knowledge, repo config. **NEVER `status: approved`** (may set `status: accepted` on a NEW ADR it authors). |
| architecture-reviewer | `docs/reviews/` only | everything else. **NEVER `status: approved`** (it produces a verdict; PO or autonomy policy decides). |

**Model family rules:** reviewer family ≠ executor family; architecture-reviewer
family ≠ Architect family. Enforced by orchestrator routing; a same-family reviewer
must refuse and ask to be re-routed.

## Hard rules

1. **Never skip upstream.** No Ticket without an approved ArchSpec. No ArchSpec without an approved PRD.
2. **Version-pinned references only.** Reference upstream docs as `ID@X.Y.Z` (e.g. `PRD-001@1.0.0`). A bare `PRD-001` outside code fences is rejected by CI.
3. **Status gates.** `draft` (role may edit) → `in_review` (only the reviewer touches it, via a `docs/reviews/RV-*.md` file) → `approved` (immutable; any change ⇒ version bump + revision/`superseded_by`) → `superseded` (read-only). Only the PO sets `approved` — unless `project.jsonc.autonomy.arch_approval` delegates ArchSpec approval to the architecture-reviewer gate.
4. **Non-Goals / NOT-In-Scope are mandatory.** PRDs list ≥1 Non-Goal; Tickets list ≥1 NOT-In-Scope item.
5. **Architect Phase 0 Recon is mandatory.** Before designing, the Architect reads everything in `docs/knowledge/` and writes a Recon Report into ArchSpec §0. No Recon ⇒ rejected.
6. **Executor guardrails.** Modifies ONLY files in the ticket's `§5 Outputs` (plus its own ticket `status` transitions and `§10` appends). No new runtime dependencies unless `§7 Constraints` allows. Obeys every invariant in `project.jsonc.invariants`. If a ticket is ambiguous or contradicts the ArchSpec, STOP and file `docs/questions/Q-TKT-NNN-NN.md`.
7. **Reviewer independence.** Reviewer model family ≠ executor; architecture-reviewer family ≠ Architect.
8. **No secrets in git.** Ever. Use `.env.example`; document in ArchSpec §9 Security. `opencode.json` blocks `.env*` writes — do not work around it.
9. **No direct push to `main`.** All changes via PR; each Ticket gets its own PR. A PR merges only with: docs CI green, reviewer verdict `pass`/`pass_with_changes`, and the `project.jsonc` code checks green.
10. **One TKT, one PR.** No aggregating tickets; no splitting one ticket across PRs.

## Handoff contracts

| From → To | What goes across | Gate |
|---|---|---|
| PO → Business Planner | This-epic ask (Mentor assembles the session block) | — |
| Business Planner → PO | One PRD, status `draft` | BP runs `validate_docs.py` |
| PO → Architect | One PRD, status `approved` | PO sets status |
| Architect → architecture-reviewer | ArchSpec + ADRs + Tickets, status `draft` | Architect runs `validate_docs.py` |
| architecture-reviewer → PO / autonomy gate | One arch-review file, verdict `pass`/`pass_with_changes`/`fail` | family ≠ Architect |
| PO / autonomy gate → Sisyphus | ArchSpec `approved`; tickets `ready` | `/prd-run PRD-NNN@X.Y.Z` |
| Sisyphus → executor | One Ticket `ready`, `depends_on` all `done` | per `tkt-cycle` |
| executor → reviewer (via Sisyphus) | One PR, ticket `in_review` | local checks green + self-review |
| reviewer → Sisyphus | One review file + verdict | family ≠ executor |
| Sisyphus | Merge to `main`, flip ticket `done`, append §10 | verdict pass(/with_changes), CI green |

## Parallelism (default: ON)

- The orchestrator **parallelises by default**. Two tickets run concurrently when ALL hold: their `depends_on` are satisfied (`done`), their `§5 Outputs` paths are disjoint, and neither is in the other's transitive `depends_on`.
- Concurrency is capped at `project.jsonc.orchestration.concurrency_cap` (default 3) to respect provider rate limits.
- Set `project.jsonc.orchestration.parallelism: "sequential"` to force one-at-a-time.
- The reviewer-family-≠-executor-family rule holds regardless of parallelism.

## Autonomy & approvals (configurable in project.jsonc)

- **Code PRs** already merge without per-PR PO sign-off: reviewer (different family) `pass` + green checks ⇒ Sisyphus merges. Set `autonomy.merge: "manual"` to require a PO ack.
- **ArchSpec** approval can be delegated: with `autonomy.arch_approval: "auto-on-reviewer-pass"`, the architecture-reviewer (family ≠ Architect) audits the spec against the PRD; on `pass` the spec is auto-approved and the PO gets a 1-line notice with the top risks. `"manual"` = PO approves by hand.
- **PRD** approval stays with the PO (business judgement). The BP prompt puts a 30-second *decision brief* at the top of every PRD so the PO approves decisions, not prose.
- **Risk escalation overrides autonomy:** any decision touching `autonomy.always_escalate_on` categories (business impact / cost / regulatory / irreversible) is escalated to the PO regardless of settings.

## Change requests

To change an `approved` PRD: bump its version, open a PR modifying (or superseding) it,
the Architect annotates impacted ArchSpec sections, the ArchSpec is bumped + re-reviewed,
affected Tickets are re-opened/split. **No "small tweak" reaches code silently — every
change walks the pipeline.**

## LLM hygiene

- Every session starts with **fresh context**. The skills re-read `AGENTS.md`, `CONTRIBUTING.md`, `project.jsonc`, the relevant ticket/PRD/ArchSpec, and the §4 Inputs cited. Never dump the whole repo into context — only cited inputs.
- Communication between agents is **structured** (dispatch prompts, hand-backs, frontmatter + §10 logs) — keep it compact and machine-parseable, not prose.
- If an LLM produces output outside its role, the reviewer rejects without merge. Model drift is real.
