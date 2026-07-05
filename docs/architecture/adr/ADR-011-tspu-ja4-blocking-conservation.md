---
id: ADR-011
type: adr
status: accepted
created: 2026-07-05
---

# ADR-011: Project Conservation — TSPU JA4 Client-Side Blocking

## Context

On July 4, 2026, a full deployment of ARCH-001@0.2.1 across 3 servers (RU entry, EU exit, SE mgmt+monitoring) was conducted. 9 architecture variants were tested. The result: **telemt MTProxy does not work from Russia without VPN**, regardless of server-side configuration.

Two independent TSPU research reports (`TELEMT_TSPU_DETECTION_RESEARCH_V1_2026-07.md`, `TELEMT_TSPU_DETECTION_RESEARCH_V2_2026-07.md`) identified the root cause:

1. **JA4/JA4+ fingerprinting** (June 5, 2026): TSPU matches the Telegram client's static TLS ClientHello fingerprint. This is a client-side signal — the proxy server cannot change it.

2. **Post-handshake payload analysis**: TSPU performs full TCP stream reassembly and detects MTProto patterns inside FakeTLS Application Data records (fixed zero random field, missing AEAD tags, deterministic record sizes).

**Proof**: Variant 5 (client via VPN → direct telemt on EU) works. Variant 9 (client direct → telemt on RU with self-steal LE cert, tproxy outbound) fails. Same telemt, same FakeTLS, same tls_domain. The only variable is whether TSPU sees the client's ClientHello.

**telemt developers' own recommendation** (June 5, 2026): use `tdlib-obf` — a custom Telegram client with JA4 randomization. This conflicts with PRD-001@0.3.0 Non-Goal: "Building or distributing custom Telegram clients (tdlib-obf)."

## Decision

**Conserve the project.** ARCH-001@0.2.1 is technically sound and ready for production. The server-side architecture (double-hop, encrypted S2, dokodemo-door entry, self-steal domain, PROXYv1) is correct and well-designed. The blocking is a client-side problem outside the project's scope.

The project remains in a conserved state until Telegram ships an official fix for the JA4 fingerprint (bugs.telegram.org #62528, marked "Fixed" but standard clients still blocked as of July 2026). When the fix ships, telemt-mgmt will work as designed with zero architecture changes.

**No further architecture work is warranted.** Server-side FakeTLS optimisation has been exhaustively tested (9 variants) and cannot address client-side JA4 detection.

## Consequences

- **Positive:** The codebase is complete, tested (217+ tests), and deployment-ready. When Telegram fixes the client, deployment is immediate.
- **Positive:** No wasted effort on server-side approaches proven ineffective.
- **Negative:** The project cannot serve users from Russia without VPN until Telegram ships the fix.
- **Follow-ups:** Monitor bugs.telegram.org #62528 for official client updates. Test each new Telegram version from a Russian residential connection. When a version works, deploy immediately.

## Alternatives considered

- **Revise PRD Non-Goal to allow tdlib-obf** — rejected by PO: users should not need to install custom clients.
- **Pivot to VLESS-Reality VPN distribution** — rejected by PO: fundamentally different product, no `tg://proxy` links, no ad_tag.
- **Hybrid model (tg://proxy + VLESS configs)** — rejected by PO: users get only `tg://proxy` links.
- **Wait for Telegram fix without conserving** — rejected: project should be polished and ready, not abandoned.

## Conservation status

- **PRD-001@0.3.0**: approved, no changes needed (constraints document TSPU environment)
- **ARCH-001@0.2.1**: approved, server-side architecture valid
- **25 tickets**: all done after final cleanup pass (TKT-025@0.2.1.2.1, TKT-026@0.2.1.2.1)
- **Monitoring**: check bugs.telegram.org #62528 monthly
- **Reactivation trigger**: Telegram client update where standard client + telemt works from Russian federal ISPs (MTS, YOTA, MegaFon, Rostelecom)
