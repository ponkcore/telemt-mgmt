# AGENTS.md

A **four-role SDLC pipeline** with strict separation of duties. Project state lives
in version-controlled markdown (docs-as-code), not in any agent's memory. The stack
(language, build/test commands, conventions, invariants) is declared in **one file**:
`.opencode/project.jsonc`. Nothing else hardcodes a language or tool.

## The pipeline

```
PO ↔ Mentor (opencode primary)            ← always-on; "where do we go next", debugging,
        │                                     config fixes, assembling external-LLM sessions.
        ├── prepares ──► Business Planner   (external LLM session, any runtime)
        │                     ▼ docs/prd/PRD-NNN.md (status: approved by PO)
        ├── prepares ──► Technical Architect(external LLM session, any runtime)
        │                     ▼ docs/architecture/ARCH-NNN.md + adr/ADR-NNN.md + docs/tickets/TKT-NNN.md
        │                       (audited by architecture-reviewer; approved by PO or auto per project.jsonc)
        └── hands off ──► Sisyphus orchestrator (opencode primary, omo)
                                ├── executor subagent          (code for one TKT, one PR)
                                ├── reviewer subagent          (reviews PR; family ≠ executor)
                                ├── architect-consult subagent (in-flight ArchSpec/ADR patch fixes)
                                └── architecture-reviewer      (audits ArchSpec vs PRD; family ≠ Architect)
                                            ▼ merged on main
```

## Roles (full write-zones in CONTRIBUTING.md)

| Role | Runs | Write-zone (summary) |
|---|---|---|
| Product Owner (human) | — | Anything. Sole authority for `status: approved` on PRDs (always) and ArchSpecs (unless delegated in `project.jsonc`). |
| **Mentor** | opencode primary | process files: `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `opencode.json`, `.opencode/**`, `docs/backlog|questions|drafts/`, `.gitignore` |
| Business Planner | any LLM, any runtime | `docs/prd/`, `docs/roadmap/` |
| Technical Architect | any LLM, any runtime | `docs/architecture/`, `docs/tickets/` |
| **Sisyphus** orchestrator | opencode primary (omo) | ticket frontmatter promotion only; delegates to subagents |
| executor (subagent) | opencode subagent | code zones from `project.jsonc` + assigned ticket's §5 Outputs + own status/§10 log |
| reviewer (subagent) | opencode subagent, **family ≠ executor** | `docs/reviews/` only |
| architect-consult (subagent) | opencode subagent | `docs/architecture/**` (patch fixes + new ADRs), `docs/backlog/**`, `docs/questions/**` |
| architecture-reviewer (subagent) | opencode subagent, **family ≠ Architect** | `docs/reviews/` only |

The Business Planner and Architect are model-agnostic (PO picks per session) and their sessions
are **interactive**: the BP interrogates the PO to co-form the product vision before writing the
PRD; the Architect designs autonomously but pauses to ask the PO at genuine decision forks. Their
runtime-agnostic prompts live at `docs/prompts/business-planner.md` and `docs/prompts/architect.md`. Mentor and Sisyphus are opencode primaries (switch with
`Tab`). Pipeline-role models (mentor, executor, reviewer, architect-consult,
architecture-reviewer) live in `.opencode/agents/<name>.md` and are set via
`python3 scripts/set-models.py`. omo's built-in agents/categories take their models from your
**system** omo config (`~/.config/opencode/oh-my-openagent.json`), not from this repo.

## How to start work (any agent)

1. Identify your role; load its file (table below).
2. Read `.opencode/project.jsonc` — your stack, commands, conventions, invariants.
3. Confirm your write-zone in `CONTRIBUTING.md`. Crossing it = reviewer reject (or, for code, blocked by `opencode.json`).
4. Run `python3 scripts/validate_docs.py` before pushing. CI runs the same check.

| Role | Files to load |
|---|---|
| Mentor | `AGENTS.md` + `CONTRIBUTING.md` + `.opencode/agents/mentor.md` |
| Business Planner | `docs/prompts/business-planner.md` |
| Technical Architect | `docs/prompts/architect.md` |
| Sisyphus | `AGENTS.md` + `CONTRIBUTING.md` + the relevant skill in `.opencode/skills/` |
| executor / reviewer / architect-consult / architecture-reviewer | `.opencode/agents/<name>.md` |

The Architect's **Phase 0 Recon is mandatory**: read everything in `docs/knowledge/`
before designing, and write a Recon Report into ArchSpec §0.

## Slash commands

- `/project-setup` — generate (or regenerate) `.opencode/project.jsonc` from a plain-language
  project + stack description, so the PO never hand-authors the config.
- `/prd-run PRD-NNN@X.Y.Z` — orchestrate a whole PRD. Sisyphus walks the `depends_on`
  DAG, parallelising independent tickets up to `project.jsonc`'s `concurrency_cap`.
- `/tkt-run TKT-NNN` — single ticket cycle.
- `/arch-review ARCH-NNN@X.Y.Z` — dispatch the architecture-reviewer to audit an
  ArchSpec against its PRD before approval.

Discipline lives in: `.opencode/skills/tkt-cycle/`, `.opencode/skills/prd-orchestration/`,
`.opencode/skills/arch-review/`, and `.opencode/agents/mentor.md`.
