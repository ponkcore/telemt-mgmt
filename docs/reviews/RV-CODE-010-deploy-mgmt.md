---
id: RV-CODE-010
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/13"
ticket_ref: TKT-010@0.1.0
status: in_review
created: 2026-07-03
---

# RV-CODE-010: review of TKT-010@0.1.0 (PR #13)

**Verdict:** fail  
**Summary:** Iteration 1 Highs (F-H1, F-H2, F-H3) are resolved, but a new High-severity integration bug blocks AC5: the `letsencrypt` certificates written by the deploy script are not mounted into the Angie container because a named volume is used instead of a host bind.

## Iteration 2 (2026-07-03)

### Previously reported Highs — resolved
- **F-H1 — Path resolution** — Fixed. `deploy-mgmt.sh:31-32` now sets `INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"` and `REPO_DIR="$(cd "$INFRA_DIR/.." && pwd)"`, so `infra/lib/common.sh` resolves correctly and `FRONTEND_DIST` points at the repo root `frontend/dist`.
- **F-H2 — `tmpfs` masking `/app/.venv`** — Fixed. `docker-compose.yml:31-33` now mounts only `/tmp` as a tmpfs; the installed Python virtualenv in the image is no longer masked, so the entrypoint can find `python`, `alembic`, and `uvicorn`.
- **F-H3 — certbot config dir** — Fixed. `deploy-mgmt.sh:201-207` now uses `--config-dir "$LE_DIR"`, `--work-dir "$LE_DIR"`, and `--logs-dir "$LE_DIR/logs"`, so certbot writes certificates to the local `letsencrypt/` directory instead of the host `/etc/letsencrypt`.

### New High in iteration 2
- **F-H4 — Let's Encrypt certificates not mounted into the Angie container** — `docker-compose.yml:48,100` declares `letsencrypt` as a **named volume** mounted at `/etc/letsencrypt`. The deploy script writes certificates to the host directory `infra/mgmt/letsencrypt/`, but this host directory is never mounted into the container. Consequently, the Angie container sees an empty `/etc/letsencrypt` and cannot serve HTTPS, so AC5 is still not met. Fix: replace `letsencrypt:/etc/letsencrypt:rw` with `./letsencrypt:/etc/letsencrypt:rw` and remove the `letsencrypt` named volume declaration.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [ ] Every §6 AC verifiably met — AC5 blocked by F-H4; all other ACs are met.
- [ ] project.jsonc checks green (typecheck/lint/test). *`mypy` and `ruff` pass; `pytest` fails on a pre-existing environment issue (missing `libstdc++.so.6` for greenlet) that also fails on `main`, so it is not introduced by this PR.*
- [x] All project.jsonc invariants hold in the diff — `INV-IDEMPOTENT`, `INV-SECRETS`, and `INV-DOCKER` are respected (the new F-H4 is a volume-mount wiring issue, not an invariant violation).

## Acceptance criteria
- **AC1 — idempotent** — `deploy-mgmt.sh:76` calls `load_env "$ENV_FILE"`; `prompt_for` (via `common.sh:49-82`) returns the existing value when already set, so re-runs skip prompts.
- **AC2 — prompts for required values** — `deploy-mgmt.sh:81-119` calls `prompt_for` for `TELEMT_API_URL`, `TELEMT_AUTH_HEADER`, `BOT_TOKEN`, `PANEL_DOMAIN`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `TELEMT_PROXY_SERVER`, and `TELEMT_PROXY_PORT`.
- **AC3 — PostgreSQL auto-created if DATABASE_URL not provided** — `deploy-mgmt.sh:121-134` checks `${DATABASE_URL:-}` and generates a `POSTGRES_PASSWORD` + `DATABASE_URL` pointing at the Compose `db` service.
- **AC4 — Alembic migrations run on container startup** — `Dockerfile.api:74-76` runs `alembic upgrade head` in the inline entrypoint.
- **AC5 — Admin panel accessible via HTTPS (Angie + Let's Encrypt)** — `angie.conf.template:54-61` declares the HTTPS server with Let's Encrypt paths; `deploy-mgmt.sh:193-218` attempts Let's Encrypt (or self-signed fallback). However, the certificate files are not mounted into the container due to F-H4, so the panel will not actually be reachable over HTTPS until the volume is bound to the host `letsencrypt` directory.
- **AC6 — Bot starts and connects to Telegram via long polling** — `Dockerfile.api:117-122` starts `uvicorn` and `python -m bot` in the entrypoint.
- **AC7 — shellcheck clean** — `shellcheck infra/mgmt/deploy-mgmt.sh` returns no output.

## Findings

### Resolved in iteration 2
- ~~**F-H1:** `infra/mgmt/deploy-mgmt.sh:31-32,43,171-183` — directory resolution now correct.~~
- ~~**F-H2:** `infra/mgmt/docker-compose.yml:31-33` — `/app/.venv` tmpfs removed.~~
- ~~**F-H3:** `infra/mgmt/deploy-mgmt.sh:201-207` — certbot now uses `--config-dir`, `--work-dir`, `--logs-dir`.~~

### High  (block merge)
- **F-H4:** `infra/mgmt/docker-compose.yml:48,100` — The `letsencrypt` named volume is not connected to the host `letsencrypt/` directory where `deploy-mgmt.sh` writes certificates. Angie cannot find `/etc/letsencrypt/live/<domain>/fullchain.pem` at runtime, breaking HTTPS and AC5. Replace with `./letsencrypt:/etc/letsencrypt:rw` and remove the named volume declaration.

### Medium  (fix or backlog)
- **F-M1:** `infra/mgmt/deploy-mgmt.sh:76` — `load_env` only sources the `.env` file; on a re-run after a failed partial run, variables that were never written are not present and the script may re-prompt. This is acceptable for MVP but should be hardened in a follow-up.

### Low  (optional)
- **F-L1:** `infra/mgmt/docker-compose.yml:24-39` — The `api` service has no `healthcheck`; only `db` has one. Add a simple `curl -f http://localhost:8000/api/health` healthcheck once the container starts successfully.
- **F-L2:** `infra/mgmt/deploy-mgmt.sh:207` — `--register-unsafely-without-email` bypasses Let's Encrypt account email; acceptable for an MVP one-click deploy, but operators should be warned that expiry notices will not be delivered.
- **F-L3:** `docs/tickets/TKT-010-deploy-mgmt.md:5` — `arch_ref: ARCH-001@0.1.1` is stale; the approved ArchSpec is `ARCH-001@0.1.2`.

## Red-team probes
- **error_paths:** `deploy-mgmt.sh:67` (`check_docker`) and Dockerfile entrypoint DB wait/alembic steps handle missing Docker/DB/migrations. The path and tmpfs bugs are fixed; F-H4 is a wiring error that surfaces at container runtime.
- **concurrency:** N/A — single-server deploy script.
- **input_validation:** `common.sh:70-76` rejects empty prompt values; `save_env_var` escapes `&` and `\`, but other shell/meta characters in user input are not sanitised before `sed` substitution. Admin password is bcrypt-hashed on startup.
- **authz_isolation:** Admin API and bot run in the same container per `ARCH-001@0.1.2 §3 C5`; only the frontend container exposes ports 80/443, and `/api` is proxied through Angie. No direct 8000 exposure in Compose.
- **secrets:** No secrets in the diff; `.env.example` documents all required variables; `.env` is gitignored per `INV-SECRETS`. Bot token, auth_header, DB password, JWT secret, and hashing salt are generated or prompted and persisted to `.env` only.
- **observability:** Only the PostgreSQL service has a `healthcheck`; the `api` service lacks one, making it harder to detect when the entrypoint fails.
- **rollback:** `docker compose down && up -d --build` on re-run updates configuration but provides no rollback path beyond re-running the script or restoring from a previous `.env`/volume backup. Backlog a rollback runbook.
- **dns_failover:** N/A — this ticket deploys the management server; proxy DNS is handled by the entry/exit deploy scripts.
