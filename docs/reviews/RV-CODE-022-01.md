---
id: RV-CODE-022-01
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/39"
ticket_ref: TKT-022@0.2.1
status: in_review
created: 2026-07-04
---

# RV-CODE-022-01: review of TKT-022@0.2.1 (PR #39)

**Verdict:** pass_with_changes
**Summary:** All §6 acceptance criteria are met and shell/project checks pass, but `docs-ci` is red due to a pre-existing unversioned reference in `docs/reviews/RV-CODE-020-01.md` not introduced by this PR.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `infra/entry/.env.example` contains only `EXIT_SERVER_IP`, `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`; no entry Reality keys, no `VLESS_UUID_ENTRY`, no `REALITY_PRIVATE_KEY`, no `REALITY_SNI`.
- AC2 — `infra/exit/.env.example` contains `EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_REALITY_SHORT_IDS`, and `TLS_DOMAIN=www.microsoft.com`.
- AC3 — `scripts/migrate.sh:374-392` branches on `SERVER_TYPE`: exit uses `curl http://${DOMAIN}:8080`, entry skips curl and proceeds to Docker status check.
- AC4 — `shellcheck scripts/migrate.sh` exits 0 with no warnings.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- F-M1: `docs/reviews/RV-CODE-020-01.md` references `TKT-020` without a version pin, causing `python3 scripts/validate_docs.py` to fail across the repo. Pre-existing and not touched by this PR; should be fixed or tracked for backlog so docs-ci becomes green.

### Low  (optional)
- F-L1: `infra/exit/.env.example:64` defaults `EXIT_REALITY_SNI=www.microsoft.com` while `infra/entry/.env.example:29` defaults `EXIT_REALITY_SNI=ads.x5.ru`. These are only defaults, but consider aligning the entry default comment to remind operators to copy the exact value from the exit server output to avoid mismatched SNI in production.

## Red-team probes  (one line each; N/A allowed)
- error_paths: Entry branch still falls through to Docker status check and rollback instructions on failure; error path is complete.
- concurrency: N/A — no concurrency changes.
- input_validation: `SERVER_TYPE` validated at `scripts/migrate.sh:181-184` to be `exit` or `entry` before health-check branch.
- prompt_injection: N/A — no prompt paths in this infra change.
- authz_isolation: N/A — no authz changes.
- secrets: `.env.example` files contain only empty placeholders and comments; no secrets committed; INV-SECRETS maintained.
- observability: Health-check output now explicitly differentiates exit vs. entry server paths, improving operability.
- rollback: Health-check failure still emits rollback instructions via `print_rollback_instructions` at `scripts/migrate.sh:411`.
- dns_failover: N/A — DNS update logic unchanged.
