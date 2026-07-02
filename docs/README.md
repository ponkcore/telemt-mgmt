# docs/ — the pipeline's shared memory (docs-as-code)

All project state lives here as version-controlled markdown. Agents have no shared memory;
these files ARE the memory. `scripts/validate_docs.py` (run in CI) keeps them consistent.

```
docs/
  prd/           PRD-NNN-*.md      Product requirements   (Business Planner; PO approves)
  roadmap/       ROADMAP-NNN-*.md  Sequenced epics        (Business Planner)
  architecture/  ARCH-NNN-*.md     Architecture specs     (Technical Architect)
    adr/         ADR-NNN-*.md      Architecture decisions (Architect / architect-consult)
  tickets/       TKT-NNN-*.md      Work units, 1 = 1 PR   (Architect; executor implements)
  reviews/       RV-CODE-NNN-*.md  Code-PR verdicts       (reviewer)
                 RV-ARCH-NNN-*.md  ArchSpec audits        (architecture-reviewer)
  questions/     Q-TKT-NNN-NN-*.md Blockers raised mid-work(executor)
  backlog/       BACKLOG-NNN-*.md  Deferred Mediums       (anyone)
  knowledge/     *.md              Phase-0 Recon inputs   (humans)
  prompts/       project-setup.md, business-planner.md, architect.md   Copy-paste prompts
  drafts/        scratch                                  (Mentor / PO)
```

## Lifecycle gates
PRD (approved by PO) → ArchSpec + ADRs + Tickets (audited by /arch-review, approved by PO or
auto per `.opencode/project.jsonc`) → `/prd-run` executes tickets → PRs reviewed & merged.

## Rules that CI enforces
- Frontmatter: required fields + allowed status per artefact type.
- `id` matches filename; PRD/ARCH versions are semver.
- Cross-references are version-pinned (`ID@X.Y.Z`) and resolve (no dangling refs).
- Ticket `depends_on` references exist and form an acyclic graph.

Start every artefact from its `TEMPLATE.md` (TEMPLATE files are skipped by the validator).
