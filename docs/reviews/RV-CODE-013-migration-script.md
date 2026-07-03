---
id: RV-CODE-013
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/8"
ticket_ref: TKT-013@0.1.1
status: in_review
created: 2026-07-03
---

# RV-CODE-013: review of TKT-013 — Migration Script (PR #8)

**Verdict:** fail  
**Summary:** The migration scripts implement the required cycle and pass shellcheck, but two High findings—undeclared runtime dependencies (`dig`, `seq`) and a masked deploy failure that lets DNS update proceed to an undeployed server—block merge.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [ ] No unauthorised runtime dependency. → H2: `dig` and `seq` are not authorised by TKT-013 §7.
- [ ] Every §6 AC verifiably met. → AC1 <2 min cannot be statically verified; AC5/AC6 undermined by H1/M1.
- [ ] project.jsonc checks green. → H3: `uv run pytest -q` fails due to pre-existing greenlet/libstdc++ issue.
- [x] All project.jsonc invariants hold (INV-DOMAIN, INV-SECRETS; others N/A for bash scripts).

## Acceptance criteria
- AC1 — `scripts/migrate.sh:38-49` timing wrapper prints elapsed; <2 min target cannot be statically verified (runtime measurement required).
- AC2 — `scripts/migrate.sh:346-360` calls `scripts/cloudflare-dns.sh:121-162` to PATCH Cloudflare A-record.
- AC3 — `scripts/cloudflare-dns.sh:25,129-136` sets TTL=60; `scripts/migrate.sh:353` reports TTL=60.
- AC4 — `scripts/migrate.sh:197-199,229-259` tars `/opt/telemt` config/state and verifies size.
- AC5 — `scripts/migrate.sh:362-422` performs DNS/curl/Docker health check (but does not fail the script on failure — M1).
- AC6 — `scripts/migrate.sh:86-121` prints rollback instructions; invoked on all error paths.
- AC7 — `shellcheck scripts/migrate.sh` passes (no output).
- AC8 — `shellcheck scripts/cloudflare-dns.sh` passes (no output).
- AC9 — `scripts/migrate.sh:123-148,430-431` outputs `curl -s https://<domain> && echo OK` and additional verification commands.

## Findings
### High (block merge)
- F-H1: `scripts/migrate.sh:331-338` — Deploy script failure is masked by `... || echo 'DEPLOY_WARNING...'`, so `if ssh ...; then` always succeeds. The script continues to update DNS even if the new server was never deployed, defeating AC5/AC6 safety. Return the real exit code and abort/escalate on deploy failure.
- F-H2: `scripts/migrate.sh:141-145,370-371` — Uses `dig` and `seq` (`scripts/migrate.sh:370`), which are not authorised by TKT-013 §7 Constraints (tar, scp, curl, jq). `dig` is absent in this environment; `seq` is not universal. Replace `seq` with a C-style `for` loop and remove or replace `dig` with a tool covered by the constraint (or update the constraint via PO/Architect).
- F-H3: `uv run pytest -q` fails on the current environment with pre-existing `greenlet`/`libstdc++.so.6` errors (same on `origin/main`). Not introduced by this PR, but the `project.jsonc` test command fails and must be green before merge per hard checks.

### Medium (fix or backlog)
- F-M1: `scripts/migrate.sh:411-431` — Health check failure does not cause a non-zero exit; the script continues to STEP 8 and prints “Migration complete!” even when the new server was not verified. Exit with an error after printing rollback instructions.
- F-M2: `scripts/migrate.sh:172-177` — No input validation for IP addresses, domain, or token format. Cloudflare token/zone/record IDs are opaque; at minimum validate IPv4/IPv6 syntax and that `SERVER_TYPE` is `exit|entry`.
- F-M3: `scripts/cloudflare-dns.sh:80-83` — `--proxied` accepts any string; only `true|false` should be allowed, otherwise the jq payload will be invalid.
- F-M4: `scripts/migrate.sh:172-177` — Interactive prompts echo the Cloudflare API token on the terminal; mask sensitive input with `read -s`.

### Low (optional)
- F-L1: `scripts/migrate.sh:99-105` — Rollback instructions echo `$CF_API_TOKEN`, `$CF_ZONE_ID`, `$CF_RECORD_ID` literally; the operator must re-enter values or export them. Consider emitting the concrete values or a reusable export block.
- F-L2: `scripts/migrate.sh:190` — `REMOTE_CONFIG_PATH` is hardcoded to `/opt/telemt`; make it configurable via env var or argument.

## Red-team probes
- error_paths: F-H1 masks deploy failures; F-M1 masks health-check failures—both lead to false “success” states.
- concurrency: No concurrent execution concerns in a single migration; risk is operator running multiple migrations for the same FQDN before DNS TTL expires (split-brain).
- input_validation: F-M2: IP/domain/Cloudflare token not validated; F-M3: `--proxied` accepts arbitrary strings.
- authz_isolation: Cloudflare API token is passed as a command-line argument to `cloudflare-dns.sh` and may appear in process listings/shell history; prefer env var or stdin.
- secrets: F-M4: API token is echoed during interactive prompt; use `read -s` or env var.
- observability: Output is human-readable only; failures do not produce a machine-parseable status, and health-check failure does not return non-zero (F-M1).
- rollback: AC6 rollback instructions are printed on all failures, but the script never auto-executes rollback and incorrectly continues to “Migration complete!” (F-M1).
- dns_failover: DNS is updated only after deploy (good), but there is no automatic DNS rollback on health-check failure (F-M1); TTL=60 is correctly requested (AC3).
