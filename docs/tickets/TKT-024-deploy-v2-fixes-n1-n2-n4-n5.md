---
id: TKT-024
type: ticket
status: in_review
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: S
created: 2026-07-04
---

# TKT-024: Deploy v2 fixes — N1 telemt read_only, N2 healthcheck path, N4 Reality SNI default, N5 flow mismatch

## §1 Goal
Fix 4 bugs found during 2nd test deployment (TELEMT_DEPLOY_REPORT_V2_2026-07-04.md): telemt container unhealthy due to read_only and healthcheck path, VLESS-Reality tunnel blocked by www.microsoft.com SNI, and flow field mismatch between entry/exit templates.

## §2 In Scope

| # | Issue | Fix |
|---|-------|-----|
| N1 | telemt `read_only: true` breaks /app writable files (beobachten, cache) | Add `user: "0:0"` to telemt service, remove `read_only: true` |
| N2 | telemt healthcheck looks for `/app/config.toml` but config is at `/etc/telemt/config.toml` | Add volume mount `./config/config.toml:/app/config.toml:ro` |
| N4 | `www.microsoft.com` breaks VLESS-Reality handshake (uTLS hang) | Change `EXIT_REALITY_SNI` default in deploy-exit.sh from `www.microsoft.com` to `ads.x5.ru` |
| N5 | Entry outbound has `flow: "xtls-rprx-vision"` but exit inbound client doesn't | Remove `flow` from entry outbound template (not needed for transparent TCP relay) |

## §3 NOT In Scope
- N3 (tls_emulation fetch fails, non-blocking) — backlogged as BACKLOG-008
- Code files (api/, telemt_proxy/, bot/) — no code changes needed
- deploy-entry.sh — N4/N5 fixes are in xray-config.json.template only (entry template uses __EXIT_REALITY_SNI__ placeholder which propagates automatically)

## §4 Inputs
- `docs/knowledge/TELEMT_DEPLOY_REPORT_V2_2026-07-04.md` — issues N1, N2, N4, N5
- ARCH-001@0.2.1 §3 C5, C7
- ADR-009@0.2.1
- GitHub issue #43

## §5 Outputs
- `infra/exit/docker-compose.yml` — N1 (user, read_only), N2 (volume mount)
- `infra/exit/deploy-exit.sh` — N4 (EXIT_REALITY_SNI default: www.microsoft.com → ads.x5.ru)
- `infra/exit/xray-config.json.template` — N4 (dest/serverNames follow default), N5 (remove flow from client if present)
- `infra/entry/xray-config.json.template` — N5 (remove `flow` from outbound user)

## §6 Acceptance Criteria
- [ ] AC1 — telemt service in exit docker-compose.yml has `user: "0:0"` and no `read_only: true`.
- [ ] AC2 — telemt service has volume mount `./config/config.toml:/app/config.toml:ro` (or healthcheck override pointing to `/etc/telemt/config.toml`).
- [ ] AC3 — `deploy-exit.sh` default for `EXIT_REALITY_SNI` is `ads.x5.ru` (not `www.microsoft.com`).
- [ ] AC4 — Entry xray-config.json.template outbound user has NO `flow` field (or exit inbound client has matching `flow` — choose one, not both).
- [ ] AC5 — `validate_docs.py` passes.
- [ ] AC6 — `shellcheck` passes on deploy-exit.sh.

## §7 Constraints
- No new dependencies.
- N4 fix is config-only — does not change ADR-009@0.2.1 architecture. The Reality SNI for the entry→exit tunnel is an operator-chosen parameter; `ads.x5.ru` is the verified-working default.
- Reality SNI (entry→exit tunnel) and FakeTLS domain (telemt client-facing) are independent. FakeTLS domain stays `www.microsoft.com` — N4 only affects Reality SNI.

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created from 2nd deploy report (issue #43).
- 2026-07-04 opencode-executor: started; implemented N1 (user:"0:0", removed read_only), N2 (/app/config.toml:ro mount), N4 (EXIT_REALITY_SNI default ads.x5.ru), N5 (removed flow from entry outbound). Checks: typecheck pass, lint pass, tests 218 pass, validate_docs pass, shellcheck pass. PR #44 opened.
