---
id: RV-CODE-014-02
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/17"
ticket_ref: TKT-014@0.1.0
status: in_review
created: 2026-07-04
---

# RV-CODE-014-02: review of TKT-014@0.1.0 Russian Reality SNI Defaults (PR #17, iteration 2)

**Verdict:** pass
**Summary:** F-H1 is resolved by replacing the `[[ -n ]]` idempotency check with a `grep -q "^REALITY_SNI_SECONDARY="` key-existence check, and all AC1-AC7 criteria are verifiably met.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (`infra/entry/deploy-entry.sh`, `infra/entry/xray-config.json.template`) plus ticket status/§10.
- [x] No §3 NOT-In-Scope term touched (fingerprint remains `firefox`, `freedom` outbound untouched, no exit-server config changes, no whitelist validation).
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (ruff, pytest, shellcheck, validate_docs).
- [x] All project.jsonc invariants hold; INV-IDEMPOTENT is satisfied.

## Acceptance criteria
- **AC1** — `deploy-entry.sh:72-74` defaults `REALITY_SNI` to `ads.x5.ru`.
- **AC2** — `deploy-entry.sh:77-90` prompts for optional `REALITY_SNI_SECONDARY` on first run.
- **AC3** — `deploy-entry.sh:173-178` builds a single-entry `serverNames` body when `REALITY_SNI_SECONDARY` is empty; verified empirically: `serverNames == ["ads.x5.ru"]`.
- **AC4** — Same logic produces two entries when secondary is set; verified empirically: `serverNames == ["ads.x5.ru", "ya.ru"]`.
- **AC5** — `xray-config.json.template:29` sets `dest` to `__REALITY_SNI__:443`, substituted with `ads.x5.ru:443`.
- **AC6** — Generated JSON parsed successfully with `json.loads`; `jq .` clean on substituted output.
- **AC7** — `deploy-entry.sh:82` uses `grep -q "^REALITY_SNI_SECONDARY=" "$ENV_FILE"` so an empty value in `.env` is detected and the prompt is skipped on re-run (empirical test passed for empty, non-empty, and missing key cases).

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- none

### Low  (optional)
- none

## Red-team probes
- **error_paths:** `grep` failure path is silenced with `2>/dev/null`, so a missing `.env` file correctly falls through to the interactive prompt.
- **concurrency:** N/A — deploy script is single-user/interactive; no concurrent access pattern introduced.
- **input_validation:** N/A — this ticket only changes SNI defaults and optional secondary SNI wiring; validation of SNI format is out of scope per §3.
- **authz_isolation:** N/A — no authz boundary changed.
- **secrets:** No secrets logged; private key and short IDs handling unchanged.
- **observability:** N/A — no logging/metrics changes.
- **rollback:** N/A — rollback strategy unchanged; `.env` remains the source of truth.
- **dns_failover:** N/A — secondary `serverNames` is a list of candidate SNIs, not a DNS failover mechanism.
