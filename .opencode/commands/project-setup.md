---
description: Generate (or regenerate) .opencode/project.jsonc from a plain-language project + stack description, instead of hand-editing it. Mentor packages the genesis session, dispatches the project-setup prompt, ingests the result, and validates it.
---

You are running project genesis: producing .opencode/project.jsonc for the PO so they never
hand-author it.

PO's description / stack from user: $ARGUMENTS

Follow this:
1. If $ARGUMENTS is thin, ask the PO ONE consolidated question: what the project is, the stack
   (or "recommend one"), and any compliance/perf constraints. Don't over-ask.
2. Assemble a one-block genesis session from docs/prompts/project-setup.md: inline the prompt,
   the PO's description, and the current .opencode/project.jsonc if one already exists (for a
   regeneration). The PO can paste this into any external LLM, OR you may dispatch it to a
   capable subagent (oracle / a deep category) if models are already wired.
3. Take the returned ```jsonc block. Sanity-check it parses (strip // comments + trailing commas,
   json.loads). Write it to .opencode/project.jsonc (this is in your write-zone, but it is a
   significant file — confirm with the PO before overwriting an existing one).
4. Run `python3 scripts/validate_docs.py` (it won't fail on project.jsonc, but confirms the repo
   is still consistent), and eyeball that commands/conventions look runnable for the stack.
5. Report to the PO: the chosen stack, the commands set, the invariants inferred, and the model
   wiring reminder (executor≠reviewer family, Architect≠architecture-reviewer family). Tell them
   the next step: run `python3 scripts/set-models.py` to wire role models (omo built-ins stay in
   the ~/.config system config), then start a BP session.

Do NOT invent business requirements (that's the BP). Do NOT set any doc to status: approved.
