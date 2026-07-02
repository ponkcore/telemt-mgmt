---
id: RV-CODE-001
type: code_review
target_ticket: TKT-001@0.1.1
pr_ref: "#1"
status: done
verdict: pass_with_changes
created: 2026-07-02
---

# RV-CODE-001: review of TKT-001@0.1.1 — Project Scaffold (PR #1)

**Verdict:** `pass_with_changes`

**Summary:** All acceptance criteria and `project.jsonc` checks pass. The scaffold is technically sound, but the PR includes a few files outside the ticket's §5 Outputs; the frontend extras are justified tooling necessities, while the new `README.md` crosses a write-zone boundary and should be noted.

## Contract compliance

- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10) — **with justified deviations documented below**.
- [x] No §3 NOT-In-Scope term touched (no business logic, no Docker Compose, no CI pipeline).
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] `project.jsonc` checks green (typecheck/lint/test).
- [x] All `project.jsonc` invariants hold (no secrets, no raw SQL, no raw Telegram IDs, etc.).

## Acceptance criteria

| AC | Requirement | Evidence | Result |
|---|---|---|---|
| AC1 | `uv sync` completes without errors | Ran `uv sync` in workspace — resolved/checked 62 packages | ✅ |
| AC2 | `cd frontend && npm ci` completes without errors | Ran `npm ci` in `frontend/` — 175 packages installed | ✅ |
| AC3 | `uv run mypy --strict telemt_proxy api bot` passes | `Success: no issues found in 3 source files` | ✅ |
| AC4 | `uv run ruff check telemt_proxy api bot tests` passes | `All checks passed!` | ✅ |
| AC5 | `uv run pytest -q` passes (0 tests OK) | `no tests ran in 0.00s` | ✅ |
| AC6 | `.env.example` contains all 11 env vars from ARCH-001 §9 | Verified all 11 secrets present (`TELEMT_AUTH_HEADER`, `BOT_TOKEN`, `DATABASE_URL`, `HASHING_SALT`, `JWT_SECRET_KEY`, `ADMIN_API_KEY`, `TELEMT_SECRET`, `AD_TAG`, `REALITY_PRIVATE_KEY`, `CLOUDFLARE_API_TOKEN`, `GRAFANA_ADMIN_PASSWORD`) | ✅ |
| AC7 | `telemt_proxy/py.typed` exists | File exists as empty marker | ✅ |

## Additional `project.jsonc` checks

| Check | Command | Result |
|---|---|---|
| TypeScript check | `npx tsc --noEmit` | ✅ (no output / no errors) |
| ESLint check | `npx eslint src` | ✅ (no output / no errors) |
| Docs validation | `python3 scripts/validate_docs.py` | ✅ `validate_docs: OK — 26 document(s) validated, 0 errors.` |

## Findings

### High (block merge)
- **None.**

### Medium (fix or backlog)
- **F-M1:** `README.md` was created by the executor but is outside the ticket's §5 Outputs and falls in the Mentor write-zone per `CONTRIBUTING.md`. It is a justified side-effect because `pyproject.toml` references it (`readme = "README.md"`), but the Mentor should own/adopt this file post-merge to keep write-zone discipline clean.
- **F-M2:** `httpx[testing]` was replaced with `respx` in `pyproject.toml` dev dependencies. The original `httpx[testing]` extra does not exist in current `httpx` releases, so the substitution is technically correct, but it is an undocumented dev-dependency change relative to the ticket's §2 In Scope list. Backlog a ticket patch or ADR note if respx is to remain the canonical test mock.

### Low (optional)
- **F-L1:** `frontend/.eslintrc.cjs` and `frontend/eslint.config.js` both exist. The legacy `.eslintrc.cjs` is inert under ESLint 9 and only kept because it is listed in §5 Outputs. Consider removing it in a follow-up to avoid confusion, or document why both configs are present.
- **F-L2:** `npm ci` reports 2 audit vulnerabilities (1 moderate, 1 high) in transitive frontend dependencies. Not blocking for a scaffold, but should be re-evaluated when real frontend code lands in TKT-007.
- **F-L3:** `frontend/vite.config.ts` proxies `/api` to `http://localhost:8000`. This is acceptable scaffold defaults, but the proxy target is hardcoded; future tickets (TKT-005/TKT-010) should make it environment-driven before production deploy.

## Red-team probes

- **error_paths:** `infra/lib/common.sh` exits on missing values in `prompt_for` and on missing Docker/Compose in `check_docker` — acceptable for a scaffold helper.
- **concurrency:** N/A — no runtime code in this scaffold.
- **input_validation:** N/A — no user input handling in scaffold files.
- **prompt_injection:** N/A — no prompt/LLM code.
- **authz_isolation:** N/A — no auth logic in scaffold; `.env.example` documents all required secrets per INV-SECRETS.
- **secrets:** No secrets committed; `.env.example` uses empty placeholders; `.env` is gitignored by existing repo config. PASS.
- **observability:** N/A — no observability code in scaffold.
- **rollback:** N/A — no deploy/rollback logic in scaffold beyond `common.sh` helpers.
- **dns_failover:** N/A.

## Verdict and recommendation

**Verdict:** `pass_with_changes`

**Recommendation:** Merge after the Mentor acknowledges/adopts `README.md` (F-M1) and records the `httpx[testing]` → `respx` substitution as an approved deviation or ticket patch (F-M2). The remaining findings are Low and can be backlogged.
