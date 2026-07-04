---
id: TKT-020
type: ticket
status: done
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: M
created: 2026-07-04
---

# TKT-020: Fix entry inbound protocol — dokodemo-door replaces VLESS-Reality

## §1 Goal
Correct the entry server's Xray inbound from VLESS-Reality (which breaks `tg://proxy` links) to `dokodemo-door` (transparent TCP forward), restoring Telegram client compatibility while preserving encrypted S2 via the VLESS-Reality outbound tunnel.

## §2 In Scope
- Rewrite `infra/entry/xray-config.json.template` with two-stage dokodemo-door + freedom proxyProtocol:1 + VLESS-Reality outbound (matching ADR-009@0.2.1)
- Update `infra/exit/xray-config.json.template` to change `xver:1` → `xver:0`
- Simplify `infra/entry/deploy-entry.sh`: remove entry Reality key/SNI/UUID prompts (entry no longer needs its own Reality credentials), fix INFRA_DIR path (D6), fix xray command format (D7)
- Revise `docs/architecture/adr/ADR-009@0.2.1-encrypted-entry-exit-vless-reality.md` to 0.2.1
- Patch `docs/architecture/ARCH-001@0.2.1-telemt-mgmt.md` §3 C5, C7, §9 (version 0.2.1)

## §3 NOT In Scope
- `infra/entry/docker-compose.yml` — owned by TKT-023@0.2.1 (D2: mount path, D5: caps)
- `infra/exit/docker-compose.yml` — owned by TKT-023@0.2.1
- `infra/exit/deploy-exit.sh` — owned by TKT-023@0.2.1 (D6, D7, D8 fixes)
- `infra/exit/config.toml.template` — owned by TKT-023@0.2.1 (D4, D8)
- Code-level fixes (api/, telemt_proxy/, bot/) — owned by TKT-021@0.2.1
- `.env.example` updates — owned by TKT-022@0.2.1
- `scripts/migrate.sh` — owned by TKT-022@0.2.1

## §4 Inputs
- ADR-009@0.2.1 (revised ADR)
- ARCH-001@0.2.1 §3 C5, C7
- `docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md` Task 3 — XRAY_DOUBLE_HOP reference config with `dokodemo-door` entry inbound (authoritative reference)
- `docs/knowledge/TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md` §3.4 — double-hop configs confirming dokodemo-door on entry
- `docs/knowledge/TELEMT_DEPLOY_REPORT_2026-07-04.md` — issue 7.11 (architectural gap)
- TKT-018@0.2.0 (predecessor — its entry template output is superseded by this ticket)

## §5 Outputs
- `infra/entry/xray-config.json.template` — **full rewrite**
- `infra/entry/deploy-entry.sh` — **significant revision** (simplified prompts, D6/D7 fixed)
- `infra/exit/xray-config.json.template` — **patch** (xver: 1 → 0)
- `docs/architecture/adr/ADR-009@0.2.1-encrypted-entry-exit-vless-reality.md` — **revision** (0.2.1)

## §6 Acceptance Criteria
- [ ] AC1 — Entry inbound protocol is `dokodemo-door` (not `vless`) on :443.
- [ ] AC2 — Entry has two-stage dokodemo-door: public-in (:443) → proxy-injector (freedom proxyProtocol:1) → tunnel-in (:10444) → proxy-to-exit (VLESS-Reality outbound).
- [ ] AC3 — Entry template has NO placeholders for `__VLESS_UUID_ENTRY__`, `__REALITY_PRIVATE_KEY__`, `__REALITY_SNI__`, `__REALITY_SERVER_NAMES__`, `__REALITY_SHORT_IDS__`. Only exit-related placeholders remain.
- [ ] AC4 — Exit template `xver` is `0` (not `1`).
- [ ] AC5 — `deploy-entry.sh` does NOT prompt for entry Reality private key, entry VLESS UUID, or entry Reality SNI. Only prompts for exit server credentials.
- [ ] AC6 — `deploy-entry.sh` `INFRA_DIR` resolves to `infra/` (one level up from script dir, not two levels up).
- [ ] AC7 — `deploy-entry.sh` xray key generation uses `docker run --rm ghcr.io/xtls/xray-core:latest x25519` (no extra `xray` prefix).
- [ ] AC8 — ADR-009@0.2.1 status is `accepted`, revision date is 2026-07-04, explains the correction from VLESS inbound to dokodemo-door inbound.
- [ ] AC9 — ARCH-001@0.2.1 version is 0.2.1, §3 C5 describes dokodemo-door entry, §3 C7 specifies `xver:0` and freedom proxyProtocol for PROXY chain.
- [ ] AC10 — `tg://proxy` link flow works: client → entry:443 (dokodemo-door) → VLESS tunnel → exit → telemt. Verify by manual config inspection (no live test required).

## §7 Constraints
- No new dependencies.
- Entry template must match the reference architecture in TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md Task 3 (XRAY_DOUBLE_HOP config).
- PROXYv1 (not PROXYv2) for consistency with ARCH-001@0.2.1 §3 C5 and mask_proxy_protocol=1.
- `fingerprint: "firefox"` on VLESS outbound (Chrome blocked since May 2026).

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
- 2026-07-04 opencode-executor: started; implementing §5 Outputs.
- 2026-07-04 opencode-executor: in_review; tests 198 pass (1 skip); lint clean; typecheck clean; shellcheck clean; validate_docs OK (57 docs, 0 errors).
- 2026-07-04 opencode-orchestrator: merged in eda986e; RV-CODE-020-01 verdict=pass_with_changes; F-M1 (ticket §5 Outputs incomplete) backlogged, F-L1 (dead config) noted.
