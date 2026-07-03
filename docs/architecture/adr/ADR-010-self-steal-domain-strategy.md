---
id: ADR-010
type: adr
status: proposed
created: 2026-07-03
---

# ADR-010: Self-Steal Domain Strategy for tls_domain

## Context
ARCH-001@0.1.2 §3 C5 uses `github.com` as the default `tls_domain` recommendation for the exit server. TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 documents that `github.com` (Azure CDN AS8075) creates an ASN mismatch against typical EU hosting (Hetzner AS24940), and MegaFon has already blocked connections based on this A-record cross-check [1]. The research proposes a "self-steal" strategy where the operator uses their own domain with DNS pointing to the exit server IP, eliminating ASN mismatch by construction.

## Decision
We will support an optional self-steal domain strategy in `deploy-exit.sh`:
1. Deploy script prompts the operator: "Do you have a domain for self-steal? (recommended for production)"
2. If yes: prompts for domain name, runs Let's Encrypt cert acquisition via Angie ACME, configures `tls_domain` to the operator's domain, sets up Angie to serve the TLS cert for `tls_emulation` fetching.
3. If no: defaults to `www.microsoft.com` (replacing `github.com` as the default recommendation).

Self-steal is documented as the recommended production approach; `www.microsoft.com` is the safe default for quick deployments.

## Consequences
- **Positive:** Eliminates ASN mismatch for operators who set up self-steal; TSPU A-record cross-check passes by construction.
- **Positive:** Operator controls domain rotation (DNS TTL update + telemt restart ≈ 30 seconds).
- **Negative / cost:** Requires domain registration and DNS management for self-steal. Adds Let's Encrypt cert management to exit server.
- **Follow-ups:** `deploy-exit.sh` must handle cert renewal (certbot/ACME cron or Angie's built-in ACME). If encrypted S2 (ADR-009@0.2.0) is also adopted, self-steal is less critical (tls_domain only matters for S3, outside Russia) but still recommended for defense in depth.

## Alternatives considered
- **Keep `github.com` as default** — rejected: ASN mismatch confirmed to trigger MegaFon blocking [1]; `www.microsoft.com` is strictly better as a third-party domain default.
- **Mandatory self-steal (no fallback)** — rejected: adds friction for operators without domain infrastructure; MVP should be deployable without domain registration.
