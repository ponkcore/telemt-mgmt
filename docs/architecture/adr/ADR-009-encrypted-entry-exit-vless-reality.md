---
id: ADR-009
type: adr
status: accepted
created: 2026-07-03
revised: 2026-07-04
---

# ADR-009: Encrypted Entry-to-Exit Segment via VLESS-Reality

## Context
ARCH-001@0.1.2 §3 C5 uses a `freedom` outbound on the entry server to redirect raw TCP to the exit server. This exposes MTProto byte patterns on the RU→EU international link (segment S2), where TSPU scrutiny is deepest. TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 and §6 document post-handshake payload analysis as an active TSPU capability since June 2026, and TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3 confirms production infrastructure "never sends raw proxy traffic on the RU→EU segment."

## Decision
We will encrypt segment S2 (entry → exit) with a VLESS-Reality tunnel. The entry server retains a **`dokodemo-door` inbound** (transparent TCP forward on :443) so Telegram clients can connect with standard MTProto/FakeTLS via `tg://proxy` links. The VLESS-Reality tunnel operates **between entry and exit only** — it is an outbound on the entry and an inbound on the exit. The architecture becomes:

- **Entry:** two-stage `dokodemo-door` inbound (:443 public → :10444 local) with `freedom` `proxyProtocol:1` between stages (PROXYv1 injection) → VLESS-Reality outbound to exit:443
- **Exit:** Xray VLESS-Reality inbound (:443, `xver:0`, from entry only) → `freedom` outbound → telemt localhost:8443 (MTProto/FakeTLS) + Angie :8080 (mask)

telemt moves from port 443 to 8443 (not externally exposed). Client IP is preserved via PROXYv1: the entry's `freedom proxyProtocol:1` prepends a PROXYv1 header into the data stream; the VLESS tunnel carries it end-to-end; telemt on exit parses it with `proxy_protocol = true`.

**Critical:** The client-facing inbound on entry is `dokodemo-door` (transparent TCP), NOT `vless`. Telegram clients speak MTProto, not VLESS. The `tg://proxy` link points to the entry server (domain, port 443). The client's FakeTLS-wrapped MTProto is forwarded transparently — the entry never interprets the protocol.

### PROXYv1 chain (client IP preservation)

```
Client → entry:443 (dokodemo-door, accepts TCP)
  ↓ routing: public-in → proxy-injector (freedom, proxyProtocol:1)
  ↓ freedom connects to 127.0.0.1:10444, prepends PROXYv1 header
  ↓ tunnel-in (dokodemo-door :10444, localhost) receives [PROXYv1 | data]
  ↓ routing: tunnel-in → proxy-to-exit (VLESS-Reality outbound)
  ↓ VLESS-Reality tunnel encapsulates: [PROXYv1 | MTProto/FakeTLS]
  → exit:443 (VLESS-Reality inbound, xver:0, no additional header)
  ↓ freedom → telemt:8443
  ↓ telemt: proxy_protocol=true → parses PROXYv1 → sees real client IP ✓
```

The exit inbound MUST have `xver:0`. With `xver:1`, the exit would prepend a *second* PROXYv1 header (containing the *entry server's* IP), causing telemt to see entry's IP instead of the real client's IP.

## Consequences
- **Positive:** MTProto patterns completely hidden from S2 DPI; international gateway sees only VLESS-Reality (standard HTTPS appearance).
- **Positive:** Post-handshake payload analysis — the strongest June 2026 detection vector — is fully mitigated on S2.
- **Positive:** `tg://proxy` links work — entry accepts standard MTProto/FakeTLS from Telegram clients. No VLESS client required.
- **Positive:** Entry server simplified — no Reality keys, no VLESS UUID, no SNI selection. Only exit server credentials needed.
- **Negative / cost:** Additional Xray process on exit server (minimal resource cost). Exit deploy script is more complex. 1–3 RTT connection setup overhead (one-time per persistent Telegram connection).
- **Negative / cost:** Entry server has no TLS/Reality facade for active probes on :443. Probes are forwarded through the tunnel to exit → telemt, which handles masking. This is acceptable per the reference architecture (TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md Task 3).

### Revision: 0.2.0 → 0.2.1

**0.2.0 (WRONG):** Entry inbound was `vless` (VLESS-Reality, client-facing). This broke `tg://proxy` links because Telegram clients speak MTProto, not VLESS. The VLESS tunnel was between *client and entry* — but it should be between *entry and exit*.

**0.2.1 (CORRECT):** Entry inbound is `dokodemo-door` (transparent TCP forward). The VLESS-Reality tunnel is between *entry outbound and exit inbound* (segment S2 only). This matches the reference architecture in TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md Task 3 (XRAY_DOUBLE_HOP verified config) and TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md §3.4.

## Alternatives considered
- **Keep `vless` inbound, generate VLESS links** — rejected: requires xray/v2ray client on user device, breaks Telegram's built-in proxy support, violates PRD-001@0.3.0 assumption that end users use standard Telegram clients.
- **XHTTP-TLS transport** — deferred: VLESS-Reality is better documented and more widely deployed in production Russian proxy infrastructure.
- **Keep `freedom` (raw TCP, no encrypted S2)** — rejected: post-handshake payload analysis is active, production systems unanimously encrypt S2.
