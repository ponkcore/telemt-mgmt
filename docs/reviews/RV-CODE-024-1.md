---
id: RV-CODE-024
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/44"
ticket_ref: TKT-024@0.2.1
status: in_review
created: 2026-07-04
---

# RV-CODE-024-1: review of TKT-024 (PR #44)

**Verdict:** pass_with_changes
**Summary:** All four fixes (N1, N2, N4, N5) are correctly implemented and verified; project checks pass, but the ticket frontmatter is still `in_progress` instead of `in_review`.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `infra/exit/docker-compose.yml:42` `user: "0:0"`; `read_only` key removed from telemt service.
- AC2 — `infra/exit/docker-compose.yml:35` `- ./config/config.toml:/app/config.toml:ro`.
- AC3 — `infra/exit/deploy-exit.sh:412-414` default `EXIT_REALITY_SNI` is `ads.x5.ru` (was `www.microsoft.com`).
- AC4 — `infra/entry/xray-config.json.template:55-59` outbound user has only `"id"` and `"encryption"`, no `"flow"`; `infra/exit/xray-config.json.template:16-20` inbound client has no `"flow"` either.
- AC5 — `python3 scripts/validate_docs.py` → `validate_docs: OK — 63 document(s) validated, 0 errors.`
- AC6 — `shellcheck infra/exit/deploy-exit.sh` → no output (success).

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- **F-M1:** `docs/tickets/TKT-024-deploy-v2-fixes-n1-n2-n4-n5.md:4` — ticket `status: in_progress`; per pipeline gate it should be `in_review` while under review. Flip before merge.

### Low  (optional)
- **F-L1:** `infra/exit/.env.example:64` — `EXIT_REALITY_SNI=www.microsoft.com` is now inconsistent with the script default `ads.x5.ru`. Out of this ticket's §5 Outputs, but operators copying the example may misconfigure. Backlog or fix in a follow-up doc tweak.

## Red-team probes  (one line each; N/A allowed)
- error_paths: N/A — config mount relies on `deploy-exit.sh` generating `config/config.toml` before `docker compose up`; pre-existing pattern, no new failure mode introduced.
- concurrency: N/A
- input_validation: N/A — `ads.x5.ru` is a valid hostname; `EXIT_REALITY_SNI` input validation unchanged.
- authz_isolation: N/A — no auth boundary changes.
- secrets: N/A — no secrets introduced in changed files.
- observability: N/A
- rollback: N/A — changes are config-only; reverting `docker-compose.yml` and the two script defaults is straightforward.
- dns_failover: N/A
