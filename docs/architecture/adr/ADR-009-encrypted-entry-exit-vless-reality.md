---
id: ADR-009
type: adr
status: proposed
created: 2026-07-03
---

# ADR-009: Encrypted Entry-to-Exit Segment via VLESS-Reality

## Context
ARCH-001@0.1.2 §3 C5 uses a `freedom` outbound on the entry server to redirect raw TCP to the exit server. This exposes MTProto byte patterns on the RU→EU international link (segment S2), where TSPU scrutiny is deepest. TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 and §6 document post-handshake payload analysis as an active TSPU capability since June 2026, and TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3 confirms production infrastructure "never sends raw proxy traffic on the RU→EU segment."

## Decision
We will replace the `freedom` outbound on the entry server with a VLESS-Reality outbound to the exit server, and add an Xray instance on the exit server (C7) to terminate this tunnel. The architecture becomes:

- **Entry:** Xray inbound (VLESS-Reality, :443, client-facing, `xver:1`) → Xray outbound (VLESS-Reality → exit:443)
- **Exit:** Xray inbound (VLESS-Reality, :443, from entry) → Xray outbound (freedom → telemt localhost:8443) + telemt on :8443 (internal) + Angie on :8080 (mask)

telemt moves from port 443 to 8443 (not externally exposed). Client IP is preserved via PROXYv1 (`xver:1` on entry inbound passes through the VLESS tunnel to telemt).

## Consequences
- **Positive:** MTProto patterns completely hidden from S2 DPI; international gateway sees only VLESS-Reality (standard HTTPS appearance).
- **Positive:** Post-handshake payload analysis — the strongest June 2026 detection vector — is fully mitigated.
- **Negative / cost:** Additional Xray process on exit server (minimal resource cost; Xray is lightweight). Exit deploy script becomes more complex (new prompts for exit Reality keys). 1–3 RTT connection setup overhead (one-time per persistent Telegram connection).
- **Follow-ups:** Exit server docker-compose switches to host network mode. Exit Xray needs its own X25519 keypair, VLESS UUID, and Reality SNI. Deploy-exit.sh must handle these new secrets. Entry Xray template changes from `freedom` to `vless` outbound.

## Alternatives considered
- **XHTTP-TLS transport** — viable alternative (wraps traffic in HTTP/2 over TLS). Deferred: VLESS-Reality is better documented, more widely deployed in production Russian proxy infrastructure, and the research §5 provides complete configs for it. XHTTP-TLS can be evaluated as a future transport option (research §10 "Explore Further" item 1).
- **Keep `freedom` (raw TCP)** — rejected: post-handshake payload analysis is active, federal operators at 0% success rate with unencrypted S2, production systems unanimously encrypt S2.
