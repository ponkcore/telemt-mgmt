---
id: ADR-008
type: adr
status: proposed
created: 2026-07-03
---

# ADR-008: Angie SNI Routing for Shared Exit Servers

## Context
ARCH-001@0.2.0 §3 C5 deploys telemt with exclusive ownership of port 443 on the exit server. Operators who co-locate telemt with other TLS-based services (e.g., a web server, another proxy instance) face port conflicts. TELEMT_TSPU_EVASION_PATTERNS.md Pattern 4 documents production infrastructure using Angie SNI stream routing to share port 443 across multiple services.

## Decision
We will add an optional `infra/exit/angie-sni-router.conf.template` that implements Angie `stream` module SNI routing on port 443. This template:
- Reads the SNI from the TLS ClientHello via `ssl_preread` (no decryption, no certificate handling)
- Routes by SNI to backend services on internal ports (e.g., telemt on :8443, other service on :8445)
- Is provided as an alternative to the default standalone deployment; the default remains unchanged
- Works with both the `freedom`-based and encrypted-S2 architectures

## Consequences
- **Positive:** Operators can share a single exit server IP across multiple TLS services, reducing cost.
- **Positive:** telemt moves to an internal port (:8443), not directly exposed — defense in depth.
- **Negative / cost:** Additional Angie configuration complexity; operators must understand SNI routing.
- **Follow-ups:** Documentation must clearly distinguish "standalone" (telemt on :443) from "shared" (Angie SNI routing on :443) deployment modes.

## Alternatives considered
- **HAProxy SNI routing** — rejected; Angie is already in the stack (C5 exit uses Angie for mask_host). Adding HAProxy introduces a new dependency.
- **Xray fallback routing** — rejected for the non-encrypted-S2 case; fallback configuration is complex and Xray-specific. For the encrypted S2 case, Xray is already on :443 and can be combined with Angie SNI routing if needed.
