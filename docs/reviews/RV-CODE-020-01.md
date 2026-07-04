---
id: RV-CODE-020-01
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/40"
ticket_ref: TKT-020@0.2.1
status: in_review
created: 2026-07-04
---

# RV-CODE-020-01: review of TKT-020 (PR #40)

**Verdict:** pass_with_changes
**Summary:** Entry inbound correctly switched to dokodemo-door, exit xver set to 0, deploy script simplified, and ArchSpec secrets inventory updated; one Medium ticket-documentation gap and one Low dead-config item remain.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10) — see F-M1.
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/test/shellcheck/validate_docs).
- [x] All project.jsonc invariants hold.

## Acceptance criteria
- AC1 — `infra/entry/xray-config.json.template:13` protocol is `dokodemo-door` on port 443.
- AC2 — `infra/entry/xray-config.json.template:9-107` routes `public-in` (:443) → `proxy-injector` (`freedom`, `proxyProtocol:1`) → `tunnel-in` (:10444) → `proxy-to-exit` (VLESS-Reality outbound).
- AC3 — `infra/entry/xray-config.json.template` contains only `__EXIT_*` placeholders; no `__VLESS_UUID_ENTRY__`, `__REALITY_PRIVATE_KEY__`, `__REALITY_SNI__`, `__REALITY_SERVER_NAMES__`, or `__REALITY_SHORT_IDS__` remain.
- AC4 — `infra/exit/xray-config.json.template:30` sets `"xver": 0`.
- AC5 — `infra/entry/deploy-entry.sh:91-121` prompts only for `EXIT_SERVER_IP`, `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`.
- AC6 — `infra/entry/deploy-entry.sh:44` sets `INFRA_DIR` to one level above the script directory (`infra/`).
- AC7 — `infra/entry/deploy-entry.sh` no longer generates entry Reality keys; the old double-`xray` command is removed.
- AC8 — `docs/architecture/adr/ADR-009-encrypted-entry-exit-vless-reality.md:4-6` shows `status: accepted` and `revised: 2026-07-04`; lines 48-52 explain the VLESS-inbound → dokodemo-door correction.
- AC9 — `docs/architecture/ARCH-001-telemt-mgmt.md:5` version is `0.2.1`; `§3 C5` (line 166) describes the two-stage dokodemo-door entry; `§3 C7` (line 193) specifies `xver: 0` and the PROXYv1 chain.
- AC10 — Manual config inspection confirms: client → entry:443 (dokodemo-door) → `proxy-injector` (PROXYv1) → `tunnel-in` → VLESS-Reality outbound → exit:443 → `to-telemt` → telemt:8443.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- **F-M1:** `docs/tickets/TKT-020-fix-entry-inbound-dokodemo-door.md` §5 Outputs omits `docs/architecture/ARCH-001-telemt-mgmt.md`, even though §2 In Scope explicitly requires patching it and the PR modifies it. Update the ticket's §5 Outputs to include this file.

### Low  (optional)
- **F-L1:** `infra/entry/xray-config.json.template:28-31` `tunnel-in` sets `address: 127.0.0.1, port: 10445`, but routing (`:102-107`) sends `tunnel-in` to `proxy-to-exit`, so the destination is overridden and this setting is dead/config-misleading. Consider removing or commenting it out.

## Red-team probes  (one line each; N/A allowed)
- error_paths: `deploy-entry.sh` now has no entry-key paths to fail; missing exit credentials are caught by `prompt_for` + `set -euo pipefail`. OK.
- concurrency: no concurrent code changed. N/A.
- input_validation: no format validation added for `EXIT_VLESS_UUID`/`EXIT_PUBLIC_KEY`/`EXIT_SHORT_ID` (pre-existing pattern). Low.
- authz_isolation: entry no longer stores Reality keys, reducing attack surface. OK.
- secrets: entry `.env` now holds only exit credentials; no entry `REALITY_PRIVATE_KEY`/`VLESS_UUID_ENTRY`. OK.
- observability: no logging/observability changes. N/A.
- rollback: idempotent re-run preserved via `.env` + `prompt_for` and `docker compose down`/`up`. OK.
- dns_failover: no DNS changes. N/A.
