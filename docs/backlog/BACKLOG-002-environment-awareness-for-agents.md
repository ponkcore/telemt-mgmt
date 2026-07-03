---
id: BACKLOG-002
type: backlog
status: in_progress
source: PO
created: 2026-07-03
---

# BACKLOG-002: Environment awareness for agents

## What

`project.jsonc` declares build/test commands (`uv sync`, `npm ci`, `uv run pytest`) but does
not describe the runtime environment. Agents (executor, reviewer) don't know they're on NixOS,
which has implications:

- Non-FHS filesystem (wheels expecting `/lib64/ld-linux-x86-64.so.2` may fail without `nix-ld`).
- `uv`-managed Python from `python-build-standalone` works on NixOS (includes own loader), but
  system-Python packages may not.
- `shell.nix` not in repo — no reproducible dev-shell.
- `AGENTS.md` / `CONTRIBUTING.md` don't mention NixOS or how to enter the dev environment.
- Deploy scripts (`infra/*/deploy-*.sh`) assume Ubuntu/Debian (`apt-get`, FHS paths) — correct
  for servers, but executor testing deploy logic locally on NixOS needs `nix-shell` or Docker.

## Why deferred (now in progress)

PRD-001@0.3.0 is complete. Addressing now: shell.nix added, project.jsonc commands wrapped in
`nix-shell --run`, environment block added, AGENTS.md updated.

## Suggested resolution (post-PRD-001@0.3.0)

1. ✅ Add `environment` block to `project.jsonc` (dev_os, dev_shell, fhs, note).
2. ✅ Add `shell.nix` to repo root (uv, nodejs_22, python312, LD_LIBRARY_PATH).
3. ✅ Add line to `AGENTS.md`: "Check `environment` — on NixOS all commands run inside nix-shell."
4. Document in `docs/knowledge/` a short note on NixOS + uv + Python compatibility.
5. Consider `flake.nix` migration for `nix develop` support.
