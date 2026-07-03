---
id: TKT-017
type: ticket
status: ready
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-018@0.2.0]
estimate: S
created: 2026-07-03
---

# TKT-017: Russian Datacenter Provider Guidance

## §1 Goal
Add Russian datacenter provider recommendations and warnings to the entry server deploy script and README, documenting the June 2026 TSPU Siberian module's subnet flagging of Selectel and Yandex.Cloud.

## §2 In Scope
- Add provider guidance banner to `deploy-entry.sh` (Beget/TimeWeb/reg.ru recommended; Selectel/Yandex.Cloud warning)
- Add a "Russian Entry Server Provider Selection" section to README.md
- Reference TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 and §6

## §3 NOT In Scope
- Automated provider detection or IP-to-ASN lookup in the deploy script
- Exit server provider guidance (exit is EU-based; no TSPU subnet flagging applies)
- Modifying deploy-entry.sh functional logic (banner text only)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (Selectel/Yandex.Cloud flag note), §3 (path-dependent matrix), §6 (Siberian module)

## §5 Outputs
- `infra/entry/deploy-entry.sh` (banner text block only)
- `README.md` (provider selection section)

## §6 Acceptance Criteria
- [ ] AC1 — `deploy-entry.sh` displays provider guidance before prompts
- [ ] AC2 — Beget, TimeWeb, reg.ru explicitly recommended
- [ ] AC3 — Selectel, Yandex.Cloud explicitly warned as Signal-1 flagged
- [ ] AC4 — README.md contains a provider comparison table with Signal 1 status
- [ ] AC5 — Documentation references TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 and §6

## §7 Constraints
- Text changes only; no functional script modifications

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
