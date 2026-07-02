---
id: RV-CODE-012
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/2"
ticket_ref: TKT-012@0.1.0
status: done
created: 2026-07-02
---

# RV-CODE-012: review of TKT-012@0.1.0 (PR #2)

**Verdict:** pass  
**Summary:** The optional `DOMAIN` handling in `deploy-landing.sh` has been fixed; the script is now idempotent for both HTTPS and HTTP-only modes. All ACs and `ARCH-001@0.1.2` §3 C6 / `ADR-007@0.1.0` requirements are met.

## Iteration 2
- **Previous review:** RV-CODE-012, verdict `fail`, one High finding (F-H1).
- **Fix verified:** commit `126571b` replaced `prompt_for "DOMAIN"` with custom `read -r DOMAIN` logic that allows an empty value and skips the prompt when `DOMAIN` is already loaded from `.env` (including `DOMAIN=` for HTTP-only). Verified by direct bash simulation of the re-run paths.
- **F-H1 status:** resolved.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `deploy-landing.sh` is idempotent: **PASS**. Re-run with `DOMAIN=` in `.env` correctly enters HTTP-only mode without prompting; re-run with `DOMAIN=example.com` correctly enters HTTPS mode. Fix in `infra/landing/deploy-landing.sh:50-60`.
- AC2 — Landing page shows a "Получить прокси" button linking to the bot: `infra/landing/html/index.html:99`.
- AC3 — Bot URL is configurable via deploy script (not hardcoded in HTML): `infra/landing/deploy-landing.sh:45-46`, `infra/landing/.env.example:8`; `__BOT_URL__` placeholder at `infra/landing/html/index.html:99`.
- AC4 — Page is responsive (works on mobile): `infra/landing/html/index.html:75` (`@media (max-width: 480px)`).
- AC5 — No JavaScript required for core functionality: verified `grep -i '<script'` returns no matches in `infra/landing/html/index.html`.
- AC6 — `shellcheck infra/landing/deploy-landing.sh` passes (verified locally, no output).

## Findings

### High (block merge)
- none (F-H1 resolved)

### Medium (fix or backlog)
- none

### Low (optional)
- **F-L1:** `infra/landing/docker-compose.yml:35-36` — `cap_add: [NET_BIND_SERVICE]` contradicts the file's own comment that it is not needed.
- **F-L2:** `infra/landing/angie.conf.template:11` — claims a port-80 → 443 redirect when TLS is enabled, but the generated config only adds a 443 block and omits the redirect.
- **F-L3:** `infra/landing/deploy-landing.sh:67` — `sed "s|__BOT_URL__|$BOT_URL|g"` is brittle if `BOT_URL` ever contains the `|` delimiter.

## Red-team probes
- **error_paths:** certbot failure and certificate copy failures propagate via `set -e`; the empty-DOMAIN prompt path is now handled.
- **concurrency:** N/A — the static landing page has no concurrent code.
- **input_validation:** `DOMAIN` and `BOT_URL` are passed through `sed`, `awk`, and shell conditionals without sanitization; malformed input can corrupt `angie.conf` or the command line.
- **authz_isolation:** N/A — static page with no authz surface.
- **secrets:** no secrets committed; only `BOT_URL` and `DOMAIN` are documented in `infra/landing/.env.example`.
- **observability:** no health/metrics endpoint or structured logging; container restart via `docker compose up -d` is the only recovery signal.
- **rollback:** no rollback script; `docker compose down`/`up -d` is not a rollback plan.
- **dns_failover:** N/A — single static page, no DNS logic.

## Checks run
- `shellcheck infra/landing/deploy-landing.sh` — pass
- `python3 scripts/validate_docs.py` — pass
- `uv run mypy --strict telemt_proxy api bot` — pass
- `uv run ruff check telemt_proxy api bot tests` — pass
- `uv run pytest -q` — pass
- `cd frontend && npx tsc --noEmit` — pass
- `cd frontend && npx eslint src` — pass
