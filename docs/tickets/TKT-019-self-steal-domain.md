---
id: TKT-019
type: ticket
status: draft
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-018@0.2.0]
estimate: M
created: 2026-07-03
---

# TKT-019: Self-Steal Domain Support for tls_domain

## §1 Goal
Add optional self-steal domain support to the exit server deploy script, enabling operators to use their own domain as `tls_domain` to eliminate ASN mismatch, and update the default third-party recommendation from `github.com` to `www.microsoft.com`.

## §2 In Scope
- Update `deploy-exit.sh` TLS_DOMAIN prompt with self-steal guidance and new default
- Add self-steal domain detection logic to `deploy-exit.sh`
- Add optional Let's Encrypt cert acquisition for self-steal domains (via certbot or Angie ACME)
- Add optional Angie HTTPS server block for serving TLS cert on self-steal domains
- Create `infra/exit/angie-selsteal.conf.template` (Angie config for self-steal HTTPS)
- Update `config.toml.template` `mask_host` and `mask_port` for self-steal mode
- Document self-steal setup in README.md

## §3 NOT In Scope
- Entry server self-steal domain (entry uses Reality SNI, not FakeTLS)
- Automated domain registration
- DNS provider integration (operator manages DNS manually or via existing Cloudflare scripts)
- Certbot renewal cron setup (document as manual step)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- ADR-010@0.2.0
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 (self-steal implementation guide)

## §5 Outputs
- `infra/exit/deploy-exit.sh` (TLS_DOMAIN prompt, self-steal detection, cert setup)
- `infra/exit/angie-selsteal.conf.template` (new file: Angie HTTPS for self-steal)
- `infra/exit/config.toml.template` (mask_host, mask_port for self-steal mode)
- `README.md` (self-steal domain setup section)

## §6 Acceptance Criteria
- [ ] AC1 — Default TLS_DOMAIN is `www.microsoft.com` (not `github.com`)
- [ ] AC2 — Deploy script detects self-steal domain (not in known third-party list) and sets `SELF_STEAL_DOMAIN` env var
- [ ] AC3 — When SELF_STEAL_DOMAIN is set, deploy script prompts for DNS verification before proceeding
- [ ] AC4 — `angie-selsteal.conf.template` exists with TLS server block for the self-steal domain
- [ ] AC5 — Config template sets `mask_host = "$TLS_DOMAIN"` and `mask_port = 443` for self-steal mode
- [ ] AC6 — Config template sets `mask_host = "$TLS_DOMAIN"` and `mask_port = 8080` for third-party mode
- [ ] AC7 — README.md documents DNS A-record setup, Let's Encrypt cert acquisition, and self-steal advantages
- [ ] AC8 — `deploy-exit.sh` is idempotent (INV-IDEMPOTENT)

## §7 Constraints
- certbot or Angie ACME for Let's Encrypt
- DNS A-record must be configured by operator before cert acquisition (certbot HTTP-01 challenge)
- No new pip/npm dependencies

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
