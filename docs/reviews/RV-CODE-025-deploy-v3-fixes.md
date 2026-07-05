---
id: RV-CODE-025
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/51"
ticket_ref: TKT-025@0.2.1
status: in_review
created: 2026-07-05
---

# RV-CODE-025: review of TKT-025@0.2.1 Deploy v3 fixes (PR #51)

**Verdict:** pass_with_changes
**Summary:** All acceptance criteria are met and project checks are green, but two Medium findings (socat binding scope and a docs contradiction) plus one Low finding (PYTHONPATH trailing colon) should be fixed or backlogged before considering the ticket fully closed.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- **AC1** — `infra/monitoring/docker-compose.yml:26-29` — Prometheus command no longer contains `--alertmanager.url`.
- **AC2** — `infra/mgmt/docker-compose.yml:76-92` — db service has no `cap_drop`/`no-new-privileges`; `api` (lines 31-37) and `frontend` (lines 63-68) retain hardening.
- **AC3** — `infra/mgmt/Dockerfile.api:53` — `export PYTHONPATH="/app:${PYTHONPATH:-}"` added so `import telemt_proxy` resolves to `/app/telemt_proxy`.
- **AC4** — `infra/exit/deploy-exit.sh:27-45` — socat workaround for `:9090`/:9091 PROXYv2 reset documented.
- **AC5** — `infra/exit/deploy-exit.sh:47-61` — self-steal documented as REQUIRED for `tls_emulation`.
- **AC6** — `infra/mgmt/deploy-mgmt.sh:167-179` — `screen -dmS` workaround for npm build timeout documented.
- **AC7** — `scripts/validate_docs.py` passed: 67 documents, 0 errors.
- **AC8** — `shellcheck infra/exit/deploy-exit.sh infra/mgmt/deploy-mgmt.sh` passed with no warnings.

## Findings

### High (block merge)
- None.

### Medium (fix or backlog)
- **F-M1** — `infra/exit/deploy-exit.sh:40-42` — The socat example systemd services use `TCP-LISTEN:9093,reuseaddr,fork` and `TCP-LISTEN:9094,reuseaddr,fork` without `bind=127.0.0.1`, so they listen on all interfaces by default. Combined with the documented `TCP:localhost:9090/9091` forwarding, this can expose metrics and the telemt API to the public internet if the operator copies the snippet without adding UFW rules. Add `bind=127.0.0.1` to both examples and document that `9093`/`9094` must be restricted to the monitoring/management source IPs.
- **F-M2** — `infra/exit/deploy-exit.sh:54-61` — The B5 comment asserts that self-steal is REQUIRED and that third-party domains "ALWAYS" fail `tls_emulation` and fall back to a fake cert. This contradicts `README.md` (self-steal section and third-party default), which still presents `www.microsoft.com` as a viable default. Reconcile the docs or add a caveat that third-party mode works for proxy operation but not for genuine `tls_emulation`.

### Low (optional)
- **F-L1** — `infra/mgmt/Dockerfile.api:53` — `export PYTHONPATH="/app:${PYTHONPATH:-}"` leaves a trailing colon when `PYTHONPATH` is unset, causing Python to include the current working directory in `sys.path`. Prefer `export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"`.

## Red-team probes

- **error_paths:** B1 removal of `--alertmanager.url` eliminates the Prometheus restart loop; B4 socat docs do not describe failure handling if socat exits, though systemd restart would cover it.
- **concurrency:** N/A — no concurrent code paths were modified.
- **input_validation:** The documented socat workaround (F-M1) is unsafe as copied because it binds to all interfaces; it needs `bind=127.0.0.1` and IP-restricted firewall rules.
- **authz_isolation:** B2 only relaxes hardening for the PostgreSQL `db` service; `api` and `frontend` retain `cap_drop: [ALL]` and `no-new-privileges:true`.
- **secrets:** No secrets, tokens, or credentials leaked in comments or diff.
- **observability:** Removing the invalid alertmanager flag is correct for Prometheus v2.54.1; Prometheus will start without it and no alertmanager service is configured in this compose.
- **rollback:** B2 cap_drop removal is documented in the compose comment and reversible by reverting the file; B4/B5 are docs-only additions.
- **dns_failover:** N/A — this diff does not touch DNS or failover logic.

## Project checks executed
- `nix-shell --run 'uv run pytest -q'` — 217 passed, 1 skipped.
- `nix-shell --run 'uv run ruff check telemt_proxy api bot tests'` — clean.
- `nix-shell --run 'uv run mypy --strict telemt_proxy api bot'` — clean.
- `nix-shell --run 'cd frontend && npx tsc --noEmit'` — clean.
- `nix-shell --run 'cd frontend && npx eslint src'` — clean.
- `shellcheck infra/exit/deploy-exit.sh infra/mgmt/deploy-mgmt.sh` — clean.
- `python3 scripts/validate_docs.py` — 67 documents, 0 errors.
