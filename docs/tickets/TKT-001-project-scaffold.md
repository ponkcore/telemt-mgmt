---
id: TKT-001
type: ticket
status: ready
arch_ref: ARCH-001@0.1.1
depends_on: []
estimate: M
created: 2026-07-02
---

# TKT-001@0.1.1: Project Scaffold

## §1 Goal

Set up the monorepo structure, dependency management (pyproject.toml + uv, package.json + npm), linting/typing configs, CI skeleton, and `.env.example` so all subsequent tickets have a working foundation.

## §2 In Scope

- `pyproject.toml` with project metadata, dependencies (fastapi, aiogram, httpx, sqlalchemy[asyncio], asyncpg, alembic, python-jose, passlib[bcrypt], pydantic, uvicorn, qrcode[pil], Pillow), dev dependencies (pytest, pytest-asyncio, pytest-cov, mypy, ruff, httpx[testing]).
- `uv.lock` generated via `uv sync`.
- Directory stubs: `telemt_proxy/__init__.py`, `api/__init__.py`, `bot/__init__.py`, `tests/__init__.py`, `infra/`, `scripts/`.
- `infra/lib/common.sh` — shared deploy helper functions (Docker check, prompt helpers, .env management). Used by all deploy scripts (TKT-008@0.1.1 through TKT-012@0.1.0).
- `frontend/package.json` with React 18, TypeScript, Vite, eslint config.
- `mypy.ini` or `pyproject.toml [tool.mypy]` with `--strict` settings.
- `ruff.toml` with project lint rules.
- `.env.example` documenting ALL env vars from ARCH-001@0.1.1 §9.
- `Makefile` (or `justfile`) wrapping `project.jsonc` commands: `make install`, `make test`, `make lint`, `make typecheck`.

## §3 NOT In Scope

- Any business logic, API endpoints, bot handlers, or database models.
- Docker Compose files (those are in deploy tickets TKT-008@0.1.1 through TKT-012@0.1.0).
- CI pipeline configuration (`.github/workflows/`) — deferred.

## §4 Inputs

- ARCH-001@0.1.1 §3 (component names and directory structure)
- ARCH-001@0.1.1 §9 (secrets inventory for .env.example)
- `.opencode/project.jsonc` (commands, conventions)

## §5 Outputs

- `pyproject.toml`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/.eslintrc.cjs`
- `telemt_proxy/__init__.py`
- `telemt_proxy/py.typed`
- `api/__init__.py`
- `bot/__init__.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `.env.example`
- `Makefile`
- `infra/lib/common.sh`

## §6 Acceptance Criteria

- [ ] AC1 — `uv sync` completes without errors.
- [ ] AC2 — `cd frontend && npm ci` completes without errors.
- [ ] AC3 — `uv run mypy --strict telemt_proxy api bot` passes (empty packages, no errors).
- [ ] AC4 — `uv run ruff check telemt_proxy api bot tests` passes.
- [ ] AC5 — `uv run pytest -q` passes (0 tests collected is OK).
- [ ] AC6 — `.env.example` contains all 11 env vars listed in ARCH-001@0.1.1 §9.
- [ ] AC7 — `telemt_proxy/py.typed` exists (PEP 561 marker).

## §7 Constraints

- Authorised new dependencies: fastapi, aiogram>=3.0, httpx, sqlalchemy[asyncio]>=2.0, asyncpg, alembic, python-jose[cryptography], passlib[bcrypt], pydantic>=2.0, uvicorn, qrcode[pil], Pillow — for QR code generation in TKT-004@0.1.1.
- Frontend: react>=18, typescript, vite, eslint.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 architect: patched per RV-ARCH-001 findings M1 (qrcode deps un-deferred), M3 (common.sh added to outputs).
