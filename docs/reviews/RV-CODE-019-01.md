---
id: RV-CODE-019-01
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/21"
ticket_ref: TKT-019@0.2.0
status: in_review
created: 2026-07-04
---

# RV-CODE-019: review of TKT-019@0.2.0 (PR #21)

**Verdict:** fail
**Summary:** Self-steal detection, cert acquisition, and config templating are implemented as specified, but two High-severity issues break idempotency and the self-steal runtime.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [ ] Every §6 AC verifiably met (AC8 only partially; see findings).
- [x] project.jsonc checks green (typecheck/lint/test).
- [ ] All project.jsonc invariants hold (INV-IDEMPOTENT violated).

## Acceptance criteria
- AC1 — `infra/exit/deploy-exit.sh:123-125`: default `TLS_DOMAIN` prompt is `www.microsoft.com`.
- AC2 — `infra/exit/deploy-exit.sh:82-92,131-144`: known third-party list; non-match sets and saves `SELF_STEAL_DOMAIN`.
- AC3 — `infra/exit/deploy-exit.sh:150-176`: DNS verification `yes/no` prompt before cert acquisition.
- AC4 — `infra/exit/angie-selsteal.conf.template`: new file with `server { listen 443 ssl; ... }` block.
- AC5 — `infra/exit/deploy-exit.sh:232-234` + `config.toml.template:68,72`: self-steal sets `MASK_HOST`/`MASK_PORT` = domain/443 and substitutes into template.
- AC6 — `infra/exit/deploy-exit.sh:254-256` + `config.toml.template:68,72`: third-party sets `MASK_HOST`/`MASK_PORT` = domain/8080 and substitutes into template.
- AC7 — `README.md:197-298`: DNS A-record, Let's Encrypt HTTP-01, manual renewal, and self-steal advantages documented.
- AC8 — **Partially met**: re-run skips most prompts, but the DNS verification prompt (`deploy-exit.sh:160-176`) always runs for self-steal domains, violating `INV-IDEMPOTENT`.

## Findings
### High
- **F-H1 — DNS verification prompt re-appears on re-run, violating INV-IDEMPOTENT.**
  `infra/exit/deploy-exit.sh:131-176`: after `load_env`, the script unconditionally resets `SELF_STEAL_DOMAIN` and re-prompts the operator to confirm the DNS A-record, even when the self-steal domain is already present in `.env` and the certificate exists. The invariant requires prompts to be skipped on re-run when config exists. Fix: skip the DNS prompt when `SELF_STEAL_DOMAIN` was loaded from `.env` (and ideally when the cert already exists).

- **F-H2 — Self-steal TLS certificate path is not mounted into the Angie container, so the :443 TLS server block cannot start.**
  `infra/exit/angie-selsteal.conf.template:83-84` references `/etc/letsencrypt/live/<domain>/fullchain.pem` and `privkey.pem`, but `infra/exit/docker-compose.yml:73-75` only mounts `./mask` and `./angie.conf`. The certbot step writes certs on the host, and `network_mode: host` does not share the host filesystem. The result is a failed container start in self-steal mode. Fix: either add an `/etc/letsencrypt:/etc/letsencrypt:ro` mount to `docker-compose.yml` (requires ticket/ArchSpec update), or copy the cert/key into a mounted directory (e.g. under `./mask/certs/`) and reference that path in the Angie config.

### Medium
- *none*

### Low
- **F-L1 — Stopping `telemt-mask` to free port 80 is unnecessary in the default template.**
  `infra/exit/deploy-exit.sh:200`: the default `angie.conf.template` does not listen on :80, so this stop is defensive but harmless.

## Red-team probes
- error_paths: F-H2 — self-steal deployment fails at runtime because cert files are not mounted; F-H1 — re-run forces redundant DNS confirmation.
- concurrency: N/A — no new concurrent paths introduced.
- input_validation: N/A — `TLS_DOMAIN` is used as-is in `sed` and `certbot -d`; domain characters are restricted by DNS naming, but no extra validation required by ticket.
- authz_isolation: N/A — no authz changes.
- secrets: N/A — no secrets committed; cert paths are host paths, not secrets.
- observability: N/A — no logging/telemetry changes.
- rollback: N/A — no rollback mechanism added or removed.
- dns_failover: N/A — DNS management remains manual per NOT-In-Scope.

## Files reviewed
- `infra/exit/deploy-exit.sh`
- `infra/exit/angie-selsteal.conf.template`
- `infra/exit/config.toml.template`
- `README.md`
- `docs/tickets/TKT-019-self-steal-domain.md`
- `infra/exit/docker-compose.yml` (context only, not in diff)
- `infra/lib/common.sh` (context only, not in diff)

## Check results
- `nix-shell --run 'uv run ruff check telemt_proxy api bot tests'` — passed
- `nix-shell --run 'uv run pytest -q'` — passed
- `python3 scripts/validate_docs.py` — passed (50 documents, 0 errors)
- `shellcheck infra/exit/deploy-exit.sh` — passed (no output)
