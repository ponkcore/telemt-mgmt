---
id: TKT-022
type: ticket
status: done
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: S
created: 2026-07-04
---

# TKT-022: Infra bugfixes — .env.example staleness, migrate.sh health check

## §1 Goal
Fix 2 infra-level issues from RV-CODE-FULL: M4 (stale .env.example files) and M5 (migrate.sh health check fails for entry servers).

## §2 In Scope
- M4: Update `infra/entry/.env.example` — change `REALITY_SNI` default to `ads.x5.ru`, **remove** entry-specific Reality variables (no longer needed after TKT-020@0.2.1), keep only exit-related variables. Update `infra/exit/.env.example` — change `TLS_DOMAIN` default to `www.microsoft.com`, add exit Reality variables (`EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_REALITY_SHORT_IDS`).
- M5: Fix `scripts/migrate.sh` health check — add `SERVER_TYPE` conditional: exit servers use `http://${DOMAIN}:8080` (Angie mask); entry servers skip curl and go straight to Docker status check (entry runs VLESS-Reality / dokodemo-door, not HTTP).

## §3 NOT In Scope
- `infra/entry/xray-config.json.template` — owned by TKT-020@0.2.1.
- `infra/entry/deploy-entry.sh` — owned by TKT-020@0.2.1.
- `infra/exit/xray-config.json.template` — owned by TKT-020@0.2.1.
- `infra/*/docker-compose.yml` — owned by TKT-023@0.2.1.
- `infra/exit/deploy-exit.sh` — owned by TKT-023@0.2.1.
- `infra/exit/config.toml.template` — owned by TKT-023@0.2.1.
- Code files (api/, telemt_proxy/, bot/) — owned by TKT-021@0.2.1.
- M2 (exit xver) — subsumed by TKT-020@0.2.1.

## §4 Inputs
- `docs/reviews/RV-CODE-FULL-telemt-mgmt.md` — findings M4, M5
- ADR-009@0.2.1 (entry no longer has its own Reality keys)
- `infra/entry/deploy-entry.sh` (after TKT-020@0.2.1) for correct variable list
- `infra/exit/deploy-exit.sh` for correct exit variable list

## §5 Outputs
- `infra/entry/.env.example`
- `infra/exit/.env.example`
- `scripts/migrate.sh`

## §6 Acceptance Criteria
- [ ] AC1 — `infra/entry/.env.example` contains only exit-related variables: `EXIT_SERVER_IP`, `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`. No entry Reality keys, no `VLESS_UUID_ENTRY`, no `REALITY_PRIVATE_KEY`, no `REALITY_SNI`.
- [ ] AC2 — `infra/exit/.env.example` contains all exit variables including `EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_REALITY_SHORT_IDS`. `TLS_DOMAIN` default is `www.microsoft.com`.
- [ ] AC3 — `scripts/migrate.sh` health check differentiates by `SERVER_TYPE`: exit uses HTTP check (Angie :8080), entry skips curl and uses Docker status check.
- [ ] AC4 — `migrate.sh` shellcheck-clean (no new warnings).

## §7 Constraints
- No new dependencies.
- `.env.example` must remain valid env file format (KEY=value, comments with #).

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
- 2026-07-04 opencode-executor: started; implementing §5 Outputs.
- 2026-07-04 opencode-executor: in_review; ruff pass, pytest 197 pass/1 skip, shellcheck clean, validate_docs OK; all §6 AC met.
- 2026-07-04 opencode-orchestrator: merged in 5de9d7f; RV-CODE-022-01 verdict=pass_with_changes; F-M1 (pre-existing docs-ci) fixed on main, F-L1 (SNI default mismatch) noted.
