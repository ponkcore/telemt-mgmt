---
id: TKT-018
type: ticket
status: ready
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-015@0.2.0]
estimate: L
created: 2026-07-03
---

# TKT-018: Encrypted Entry-to-Exit Segment via VLESS-Reality

## §1 Goal
Replace the `freedom` (raw TCP) outbound on the entry server with a VLESS-Reality encrypted tunnel to the exit server, and add an Xray instance on the exit server to terminate this tunnel and forward decrypted traffic to telemt on localhost:8443.

## §2 In Scope
- Replace entry `xray-config.json.template` with encrypted S2 variant:
  - Change inbound `xver` from `0` to `1` (PROXYv1 client IP preservation)
  - Replace `freedom` outbound with `vless` outbound (VLESS-Reality to exit)
  - Add new placeholders: `__VLESS_UUID_ENTRY__`, `__EXIT_VLESS_UUID__`, `__EXIT_REALITY_SNI__`, `__EXIT_SHORT_ID__`, `__EXIT_PUBLIC_KEY__`
- Create exit `xray-config.json.template` (new file):
  - VLESS-Reality inbound on :443 (from entry server)
  - Freedom outbound to `127.0.0.1:8443` (to telemt)
- Update exit `docker-compose.yml`:
  - Add `xray-exit` service container
  - Switch all services to host network mode
- Update exit `config.toml.template`: change port from 443 to 8443
- Update `deploy-entry.sh`: add prompts for exit VLESS UUID, exit Reality public key, exit Reality SNI, exit short ID
- Update `deploy-exit.sh`: add Xray keypair generation, VLESS UUID generation, xray-config.json generation from template, updated UFW rules

## §3 NOT In Scope
- XHTTP transport alternative (deferred per ADR-009@0.2.0)
- Angie SNI routing integration (handled by TKT-016@0.2.0)
- Self-steal domain for exit Reality SNI (handled by TKT-019@0.2.0; default: `www.microsoft.com`)
- Entry server docker-compose changes (Xray container unchanged)
- Monitoring stack changes (Prometheus scrapes same :9090)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5, C7
- ADR-009@0.2.0
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 (architecture, Xray configs, port conflict)
- TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3

## §5 Outputs
- `infra/entry/xray-config.json.template` (full replacement)
- `infra/entry/deploy-entry.sh` (exit server connectivity prompts)
- `infra/exit/xray-config.json.template` (new file)
- `infra/exit/docker-compose.yml` (updated: +xray-exit, host network)
- `infra/exit/config.toml.template` (port 443→8443)
- `infra/exit/deploy-exit.sh` (Xray setup, keypair generation, config generation)

## §6 Acceptance Criteria
- [ ] AC1 — Entry template inbound has `"xver": 1`
- [ ] AC2 — Entry template outbound protocol is `"vless"` (not `"freedom"`)
- [ ] AC3 — Entry template outbound has `"flow": "xtls-rprx-vision"` and `"security": "reality"`
- [ ] AC4 — Exit `xray-config.json.template` exists with VLESS-Reality inbound on :443
- [ ] AC5 — Exit Xray freedom outbound redirects to `127.0.0.1:8443` (no `proxyProtocol` field)
- [ ] AC6 — Exit `docker-compose.yml` includes `xray-exit` service with INV-DOCKER hardening
- [ ] AC7 — All services in exit `docker-compose.yml` use `network_mode: host`
- [ ] AC8 — Exit `config.toml.template` port is `8443`
- [ ] AC9 — `deploy-exit.sh` generates X25519 keypair for exit Xray (reusing the pattern from `deploy-entry.sh`)
- [ ] AC10 — `deploy-exit.sh` generates VLESS UUID for exit Xray (auto-generate with `uuidgen` or `xray uuid`)
- [ ] AC11 — `deploy-entry.sh` prompts for `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`
- [ ] AC12 — PROXYv1 client IP preservation verified: entry `xver:1` → VLESS tunnel → exit freedom → telemt `proxy_protocol=true` → real client IP in telemt logs
- [ ] AC13 — Both generated configs are valid JSON (`jq .` passes)
- [ ] AC14 — `deploy-exit.sh` is idempotent (INV-IDEMPOTENT)
- [ ] AC15 — All new secrets stored in `.env` (INV-SECRETS): `EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_SHORT_IDS`

## §7 Constraints
- telemt 3.4.22+ required
- Xray-core latest (ghcr.io/xtls/xray-core:latest)
- Host network mode required on exit server (for localhost:8443 communication between containers)
- No new pip/npm dependencies (deploy scripts only)

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
