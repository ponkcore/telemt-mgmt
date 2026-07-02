---
id: TKT-008
type: ticket
status: ready
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-001@0.1.1]
estimate: M
created: 2026-07-02
---

# TKT-008@0.1.1: Deploy Script — Exit Server (Telemt + Angie)

## §1 Goal

Create an interactive deploy script and Docker Compose for the EU exit server running telemt + Angie mask host.

## §2 In Scope

- `infra/exit/deploy-exit.sh` — interactive script. Prompts: domain, ad_tag, tls_domain (recommendations: `github.com` primary, `www.microsoft.com` backup), telemt secret (auto-generate option), mask host config.
- `infra/exit/docker-compose.yml` — telemt + Angie containers.
- `infra/exit/config.toml.template` — telemt config template.
- `infra/exit/angie.conf.template` — Angie config for mask_host (:8080, generic stub page).
- `infra/exit/mask/index.html` — generic stub HTML for mask_host.
- Docker hardening: `cap_drop: ALL`, `cap_add: NET_BIND_SERVICE`, `read_only: true`, `no-new-privileges`.
- Firewall rules: UFW allow 443/tcp, restrict 9090 and 9091 to specified IPs.
- `ulimit -n 65536` configuration.

## §3 NOT In Scope

- Entry server (TKT-009@0.1.1).
- Management server (TKT-010@0.1.0).
- Monitoring (TKT-011@0.1.1).
- One-pager landing page (TKT-012@0.1.0).

## §4 Inputs

- ARCH-001@0.1.1 §3 C5 (deploy-exit.sh interface)
- ARCH-001@0.1.1 §5 INV-IDEMPOTENT, INV-DOCKER, INV-SECRETS
- ADR-003@0.1.1 (five independent deploy scripts)
- PRD-001@0.3.0 §5 R7, R8, R11 (exit server requirements)
- docs/knowledge/TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md §2 (Docker hardening), §7 (production config)

## §5 Outputs

- `infra/exit/deploy-exit.sh`
- `infra/exit/docker-compose.yml`
- `infra/exit/config.toml.template`
- `infra/exit/angie.conf.template`
- `infra/exit/mask/index.html`
- `infra/exit/.env.example`

## §6 Acceptance Criteria

- [ ] AC1 — `deploy-exit.sh` is idempotent (re-running updates config without duplicating containers).
- [ ] AC2 — Script prompts for domain, ad_tag, tls_domain, telemt secret.
- [ ] AC3 — Generated `config.toml` has: `tls = true`, `mask = true`, `unknown_sni_action = "reject_handshake"`, `use_middle_proxy = true`, `config_strict = true`.
- [ ] AC4 — Docker Compose includes hardening: cap_drop ALL, read_only, no-new-privileges.
- [ ] AC5 — Angie serves mask_host on :8080 (NOT :443).
- [ ] AC6 — `.env.example` documents all required env vars.
- [ ] AC7 — Firewall rules restrict :9090 and :9091 to specified management/monitoring IPs.
- [ ] AC8 — `shellcheck infra/exit/deploy-exit.sh` passes.
- [ ] AC9 — Generated `config.toml` contains `ad_tag = "<operator-provided-value>"` in the `[general]` section.
- [ ] AC10 — Generated `config.toml` has `use_middle_proxy = true` (required for ad_tag to function).
- [ ] AC11 — Deploy script outputs a post-deploy message: 'ad_tag configured. Verify promotion at @MTProxybot /myproxies'.
- [ ] AC12 — Script includes a timing wrapper that prints total elapsed time on completion (for M1 measurement; target <10 min documented but not enforced in CI).

## §7 Constraints

- telemt Docker image: `ghcr.io/telemt/telemt:latest`.
- Angie Docker image: official Angie image.
- No Terraform/Ansible — pure bash + Docker Compose.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 architect: patched per RV-ARCH-001 findings M3 (common.sh moved to TKT-001@0.1.1), M5 (ad_tag config ACs added), L1 (timing wrapper AC added).
