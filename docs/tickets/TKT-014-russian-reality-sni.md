---
id: TKT-014
type: ticket
status: in_review
arch_ref: ARCH-001@0.2.0
depends_on: []
estimate: S
created: 2026-07-03
---

# TKT-014: Russian Reality SNI Defaults

## §1 Goal
Update the entry server Reality SNI default from `yahoo.com` to `ads.x5.ru` (Russian CDN, TSPU-whitelisted, production-validated) and support optional secondary serverNames.

## §2 In Scope
- Update `REALITY_SNI` default in `deploy-entry.sh` from `yahoo.com` to `ads.x5.ru`
- Add `REALITY_SNI_SECONDARY` prompt to `deploy-entry.sh`
- Update `xray-config.json.template` to use `__REALITY_SERVER_NAMES__` placeholder (JSON array body)
- Update template substitution logic in `deploy-entry.sh`
- Update success banner text

## §3 NOT In Scope
- Changing the `fingerprint` parameter (remains `firefox`)
- Modifying the `freedom` outbound section (handled by TKT-015@0.2.0)
- Exit server config changes
- Automated SNI validation against whitelist databases

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (top-10 candidates, validation data)
- TELEMT_TSPU_EVASION_PATTERNS.md Pattern 1

## §5 Outputs
- `infra/entry/xray-config.json.template` (inbound realitySettings section only)
- `infra/entry/deploy-entry.sh` (SNI prompt and substitution sections)

## §6 Acceptance Criteria
- [ ] AC1 — `deploy-entry.sh` default REALITY_SNI is `ads.x5.ru` (not `yahoo.com`)
- [ ] AC2 — `deploy-entry.sh` prompts for optional `REALITY_SNI_SECONDARY`
- [ ] AC3 — When REALITY_SNI_SECONDARY is empty, `serverNames` contains one entry: `["ads.x5.ru"]`
- [ ] AC4 — When REALITY_SNI_SECONDARY is set (e.g. `ya.ru`), `serverNames` contains two entries: `["ads.x5.ru", "ya.ru"]`
- [ ] AC5 — `dest` field uses primary SNI: `ads.x5.ru:443`
- [ ] AC6 — Template substitution produces valid JSON (verify with `jq .`)
- [ ] AC7 — Idempotent re-run: existing `.env` values are preserved (INV-IDEMPOTENT)

## §7 Constraints
- No new dependencies
- Must not modify the outbound section of `xray-config.json.template`

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
- 2026-07-04 opencode-executor: started — read all §4 inputs, beginning implementation of §5 Outputs.
- 2026-07-04 opencode-executor: in_review; implemented §5 Outputs, all AC verified (AC1-AC7), typecheck/lint/test green, shellcheck clean, docs-ci green.
