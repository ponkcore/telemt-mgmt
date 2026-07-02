---
id: TKT-009
type: ticket
status: done
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-001@0.1.1]
estimate: M
created: 2026-07-02
---

# TKT-009@0.1.1: Deploy Script — Entry Server (Xray VLESS-Reality)

## §1 Goal

Create an interactive deploy script and Docker Compose for the Russia entry server running Xray with VLESS-Reality.

## §2 In Scope

- `infra/entry/deploy-entry.sh` — interactive script. Prompts: exit server IP, Reality SNI (recommendations: `vkvideo.ru` for RU domestic, `yahoo.com` as telemt default), Reality keys (auto-generate option), PROXYv2 settings.
- `infra/entry/docker-compose.yml` — Xray container.
- `infra/entry/xray-config.json.template` — Xray config with VLESS inbound, Reality settings, `fingerprint: "firefox"`, PROXYv2 forwarding to exit server.
- Docker hardening.
- Firewall rules: UFW allow 443/tcp only.

## §3 NOT In Scope

- Exit server (TKT-008@0.1.1).
- AmneziaWG/VPS_DOUBLE_HOP (deprecated for Russia).
- Multiple entry servers (single entry in MVP).

## §4 Inputs

- ARCH-001@0.1.1 §3 C5 (deploy-entry.sh interface)
- ADR-003@0.1.1
- PRD-001@0.3.0 §5 R7, R8, R12
- docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md §Task 3 (XRAY_DOUBLE_HOP config)

## §5 Outputs

- `infra/entry/deploy-entry.sh`
- `infra/entry/docker-compose.yml`
- `infra/entry/xray-config.json.template`
- `infra/entry/.env.example`

## §6 Acceptance Criteria

- [ ] AC1 — `deploy-entry.sh` is idempotent.
- [ ] AC2 — Script prompts for exit server IP, Reality SNI, Reality keys.
- [ ] AC3 — Generated Xray config uses `"fingerprint": "firefox"` (NOT chrome — blocked since May 2026).
- [ ] AC4 — PROXYv2 enabled in Xray config for real client IP preservation.
- [ ] AC5 — Docker Compose includes hardening.
- [ ] AC6 — `shellcheck infra/entry/deploy-entry.sh` passes.
- [ ] AC7 — Script includes a timing wrapper that prints total elapsed time on completion (for M1 measurement; target <10 min documented but not enforced in CI).

## §7 Constraints

- Xray Docker image: `ghcr.io/xtls/xray-core:latest`.
- No Terraform/Ansible.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 architect: patched per RV-ARCH-001 finding L1 (timing wrapper AC added).
- 2026-07-03 opencode-executor: started; branch tkt/tkt-009-deploy-entry.
- 2026-07-03 opencode-executor: in_review; shellcheck pass; validate_docs pass; all 7 AC met.
- 2026-07-03 executor: fix F-M1 (shortIds JSON array format).
- 2026-07-03 opencode-orchestrator: merged in a7deeb9; RV-CODE-009 verdict=pass_with_changes (iter 2); F-M2 backlogged, F-L1/L2 non-blocking.
