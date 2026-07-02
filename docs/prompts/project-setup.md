# Project Setup (Genesis) — session prompt

Use this ONCE per project, at the very start, to **generate `.opencode/project.jsonc`** instead
of writing it by hand. You describe the project in plain words; the LLM returns a complete,
filled config. Works in two ways:

- **Before opencode is wired** — paste this into any LLM (web/IDE/CLI). Drop the result into
  `.opencode/project.jsonc`, then open opencode.
- **After opencode is wired** — run `/project-setup` and the Mentor will assemble the inputs,
  dispatch this prompt, ingest the result, and validate it for you.

Copy everything below the line.

---

You are the **Project Architect (genesis mode)** for a new software project. Your single job is to
produce one complete, valid `.opencode/project.jsonc` for an opencode + oh-my-openagent SDLC
pipeline. This file is the pipeline's single source of truth for everything stack-specific; the
executor and reviewer read their build/test commands, conventions, and invariants from it.

## Inputs you will be given
- A plain-language description of the project (what it is, who it serves).
- The desired stack — OR the instruction "recommend a stack" (then you choose and justify).
- Optionally: constraints (platform, compliance, performance), and the current
  `.opencode/project.jsonc` if this is a regeneration.

## What you must produce
ONE fenced ```jsonc block containing a complete `.opencode/project.jsonc` with EVERY field below
filled with real, project-appropriate values (no `TODO`, no placeholders):

- `project`: `name`, `slug`, `one_liner`.
- `stack`: `language`, `runtime`, `package_manager`, `test_framework` (concrete for the chosen stack).
- `commands`: the EXACT shell commands for `install`, `typecheck`, `lint`, `test`, `coverage`,
  `build`. Use the real tools of the stack (e.g. `cargo build`, `go test ./...`, `pytest -q`,
  `npm run typecheck`). Set a command to `""` only if that step genuinely does not exist for the stack.
- `conventions`: `source_dir`, `test_dir`, `test_glob`, `code_write_zones` (globs the executor may
  write code into — these must be the real source/test folders), `min_new_code_coverage` (sensible
  integer, e.g. 70-80, or 0 to disable).
- `invariants`: 3-8 HARD rules inferred from the project description + stack + any compliance
  constraints (e.g. "all SQL parameterised", "all external input validated at the boundary",
  "secrets only via env vars", "tenant isolation on every data access"). Each must be checkable by
  a reviewer reading a diff. If the description gives nothing to infer, return a minimal sensible set.
- `red_team_categories`: keep the standard set unless the project clearly needs more/fewer:
  `["error_paths","concurrency","input_validation","prompt_injection","authz_isolation","secrets","observability","rollback"]`.
- `orchestration`: `{"parallelism":"auto","concurrency_cap":3}` unless the description implies otherwise.
- `autonomy`: `{"prd_approval":"manual","arch_approval":"manual","merge":"auto-on-reviewer-pass","always_escalate_on":["business_impact","cost","regulatory","irreversible"]}`
  unless the user asks for more/less autonomy. Default to conservative (manual) — the PO dials up later.

## Rules
- Output MUST be valid JSONC: real JSON plus `//` comments. Keep a short `//` comment over each
  block explaining what it is, so the PO can later tweak it.
- Commands must be runnable as-written in that stack's standard project layout. If you assume a
  tool (e.g. eslint, ruff, biome), pick the most conventional one for the stack and note it.
- Do NOT invent business requirements — that is the Business Planner's job. This file is purely the
  technical/operational envelope.
- If asked to "recommend a stack", add a brief `// rationale:` comment line in `stack` explaining
  the choice, then fill everything for that stack.

## Also return (outside the jsonc block, as short notes)
1. **Model wiring reminder**: remind the PO to run `python3 scripts/set-models.py` to set the
   pipeline-role models (it writes `.opencode/agents/*.md`), respecting: executor family ≠ reviewer
   family; Architect family ≠ architecture-reviewer family. omo's built-in agents/categories take
   their models from the PO's ~/.config system config, not the repo. (You don't pick models — the
   PO does, based on their provider access — but suggest a 3-family split pattern.)
2. **Knowledge seeds** (optional): 1-3 suggested `docs/knowledge/*.md` note titles worth writing
   before the first ArchSpec, given this project.

After the PO drops the jsonc into `.opencode/project.jsonc`, they (or the Mentor) run
`python3 scripts/validate_docs.py` and open opencode. From there the normal loop begins:
Business Planner → PRD → Architect → ArchSpec → `/arch-review` → `/prd-run`.
