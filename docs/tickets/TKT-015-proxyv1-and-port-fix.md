---
id: TKT-015
type: ticket
status: done
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-014@0.2.0]
estimate: S
created: 2026-07-03
---

# TKT-015: PROXYv1 Protocol and Exit PROXY Config

## §1 Goal
Switch entry→exit PROXY protocol from v2 (binary, fingerprintable) to v1 (text-based) and add explicit PROXY protocol configuration to the exit server config template.

## §2 In Scope
- Change `proxyProtocol` from `2` to `1` in entry `xray-config.json.template` outbound
- Fix `redirect` port from `:8443` to `:443` in entry template (issue #14 port mismatch)
- Add `proxy_protocol = true` to exit `config.toml.template` `[server]` section
- Add `mask_proxy_protocol = 1` to exit `config.toml.template` `[censorship]` section
- Add `tls_emulation = true` to exit `config.toml.template` `[censorship]` section

## §3 NOT In Scope
- Entry inbound changes (handled by TKT-014@0.2.0)
- Self-steal domain configuration (handled by TKT-019@0.2.0)
- Encrypted S2 architecture changes (handled by TKT-018@0.2.0)
- PROXYv1 compatibility testing against telemt (documented compatible in §7 of research)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §4 (decision matrix, telemt 3.4.22 compat)
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §7 (PROXYv1 support confirmation)

## §5 Outputs
- `infra/entry/xray-config.json.template` (outbound section only)
- `infra/exit/config.toml.template` (`[server]` and `[censorship]` sections)

## §6 Acceptance Criteria
- [ ] AC1 — Entry template outbound `proxyProtocol` is `1` (not `2`)
- [ ] AC2 — Entry template outbound `redirect` port is `:443` (not `:8443`)
- [ ] AC3 — Exit template `[server]` section contains `proxy_protocol = true`
- [ ] AC4 — Exit template `[censorship]` section contains `mask_proxy_protocol = 1`
- [ ] AC5 — Exit template `[censorship]` section contains `tls_emulation = true`
- [ ] AC6 — Generated entry config is valid JSON (`jq .` passes)
- [ ] AC7 — Generated exit config is valid TOML

## §7 Constraints
- telemt 3.4.22+ required (PROXYv1 support via mask_proxy_protocol)
- No new dependencies

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
- 2026-07-04 executor: started implementation of §5 Outputs (PROXYv1, port fix, exit PROXY config)
- 2026-07-04 executor: in_review; tests pass (181 pass, 1 skip); lint clean; typecheck clean; docs-ci OK
- 2026-07-04 opencode-orchestrator: merged in f5e08ef; RV-CODE-015-01 verdict=pass; F-L1 (Low) backlog: add inline note matching mask_proxy_protocol to entry proxyProtocol.
