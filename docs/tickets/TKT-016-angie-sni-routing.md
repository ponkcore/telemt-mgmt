---
id: TKT-016
type: ticket
status: done
arch_ref: ARCH-001@0.2.0
depends_on: []
estimate: M
created: 2026-07-03
---

# TKT-016: Angie SNI Routing Template for Shared Exit Servers

## §1 Goal
Add an optional Angie SNI routing template that enables co-locating telemt with other TLS services on a shared exit server using stream-level SNI routing on port 443.

## §2 In Scope
- Create `infra/exit/angie-sni-router.conf.template` with Angie stream SNI routing
- Add `__TELEMT_SNI__` placeholder for operator's telemt SNI domain
- Include inline documentation explaining standalone vs shared mode
- Add a section to README.md documenting the shared-server deployment option

## §3 NOT In Scope
- Changing the default standalone deployment (telemt on :443 remains default)
- Modifying `deploy-exit.sh` to auto-detect shared mode (operator manually selects template)
- Docker Compose changes for the shared-server variant (operator adapts manually)
- Xray SNI routing (Xray has its own fallback mechanism; this template uses Angie)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- ADR-008@0.2.0
- TELEMT_TSPU_EVASION_PATTERNS.md Pattern 4

## §5 Outputs
- `infra/exit/angie-sni-router.conf.template` (new file)
- `README.md` (shared-server deployment section)

## §6 Acceptance Criteria
- [ ] AC1 — `angie-sni-router.conf.template` exists and contains `ssl_preread on` in a `stream` block
- [ ] AC2 — Template uses `__TELEMT_SNI__` placeholder for the telemt service SNI
- [ ] AC3 — Template routes default (unknown SNI) to telemt backend
- [ ] AC4 — Template includes the `http` block for mask host on :8080 (preserving existing mask_host functionality)
- [ ] AC5 — README.md documents standalone vs shared deployment modes with a clear comparison table
- [ ] AC6 — Template validates as syntactically correct Angie config (angie -t)

## §7 Constraints
- No new dependencies (Angie is already in the stack)
- Must not modify existing `angie.conf.template` (the default standalone template)

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
- 2026-07-04 opencode-executor: started — implementing §5 Outputs (angie-sni-router.conf.template + README.md shared-server section).
- 2026-07-04 opencode-executor: in_review; tests 198 pass (1 skip); lint clean; typecheck clean; AC1-AC5 verified, AC6 manual syntax review (angie -t requires exit server Docker image unavailable in dev env).
- 2026-07-04 opencode-orchestrator: merged in 296cec0; RV-CODE-016 verdict=pass; AC6 verified by reviewer via docker.angie.software/angie:latest (angie -t successful).
