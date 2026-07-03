# TSPU Evasion: Production-Proven Patterns for the Double-Hop Architecture (July 2026)

> **Date:** 2026-07-03
> **Scope:** Practical patterns observed in production VPN infrastructure operating in
> Russia under TSPU DPI filtering. All patterns are field-validated as of July 2026.
> No internal infrastructure details are disclosed — only technical patterns that any
> operator can replicate.

## Context

The existing `TELEMT_FAKETLS_DOMAIN_SELECTION_REPORT.md` covers TSPU detection vectors
and `tls_domain` / Reality SNI selection theory. This document complements it with
**production-proven configuration patterns** that address TSPU evasion across the
full double-hop path: client → entry (RU) → exit (EU).

Key insight from production: TSPU evasion is **path-dependent**. The techniques that
work for the client → RU entry segment differ from those needed for the RU entry →
EU exit segment. The current telemt-mgmt templates treat both segments uniformly,
which is suboptimal.

## Pattern 1: Reality SNI — Use Russian Domestic Domains on RU Entry

### Current template

`infra/entry/xray-config.json.template` uses placeholder `__REALITY_SNI__` with
default recommendation `yahoo.com` (from `deploy-entry.sh`).

### Production finding

Production VPN infrastructure operating in Russia since 2024 uses **Russian domestic
domains** as Reality `serverNames` on RU-based entry servers. These domains are
whitelisted by TSPU and their traffic from Russian IPs raises no geographic
anomaly flag.

Recommended domains (field-validated, July 2026):

| Domain | Owner | Rationale |
|---|---|---|
| `ads.x5.ru` | X5 Group (Pyaterochka, Perekrestok) | Russian retail, TSPU-whitelisted |
| `sun6-21.userapi.com` | VK (Mail.ru Group) | Russian social media CDN |
| `avatars.mds.yandex.net` | Yandex | Russian search/cloud CDN |

### Why not `yahoo.com` or `vkvideo.ru`

`yahoo.com` is the telemt XRAY_DOUBLE_HOP documented default. It works, but it is a
foreign domain on a Russian entry server — TSPU sees a TLS ClientHello with
SNI=yahoo.com originating from a Russian IP connecting to another Russian IP. This
is a geographic anomaly: real Yahoo traffic from Russia routes through Yahoo's
international PoPs, not server-to-server within Russia.

`vkvideo.ru` is a better choice (Russian domain), but production systems prefer
the X5/Yandex/VK domains above because they are **CDN/infrastructure endpoints**
rather than consumer-facing domains — their traffic patterns are noisier and harder
to fingerprint.

### Proposed change

Update `deploy-entry.sh` default `REALITY_SNI` recommendation to include Russian
domestic domains. Keep `yahoo.com` as fallback for non-RU deployments.

## Pattern 2: PROXYv1 Instead of PROXYv2 on Entry → Exit

### Current template

`infra/entry/xray-config.json.template` uses `"proxyProtocol": 2` in the `freedom`
outbound.

### Production finding

Production infrastructure uses `xver: 1` (PROXYv1) on all Reality inbounds and
cascade outbounds. PROXYv1 is a text-based protocol that resembles an HTTP request
line — it blends into HTTPS-like traffic patterns at the DPI level.

PROXYv2 is a binary protocol (12-byte signature `0x0D0A0D0A000D0A515245540A`). This
binary header is sent **before** the TLS ClientHello, creating a detectable
non-HTTPS pattern at the start of the TCP stream. DPI systems that inspect the first
bytes of a connection can distinguish PROXYv2 from real HTTPS.

### Impact of PROXYv1

PROXYv1 transmits the source IP as a text line: `PROXY TCP4 <src_ip> <dst_ip>
<src_port> <dst_port>\r\n`. telemt must support PROXYv1 header parsing for the
client IP to be preserved.

If PROXYv1 is not used, the `user_max_unique_ips` quota (config.toml) will see all
connections from the entry server's IP or docker gateway, making per-IP limits
ineffective.

### Proposed change

Change `"proxyProtocol": 2` to `"proxyProtocol": 1` in
`infra/entry/xray-config.json.template`. Verify telemt supports PROXYv1 parsing
(the telemt README mentions `use_middle_proxy = true` which enables PROXY protocol
support — need to verify v1 vs v2).

## Pattern 3: Encrypted Entry → Exit Segment

### Current template

The entry server's `freedom` outbound redirects raw TCP to the exit server. This
means MTProto traffic flows unencrypted between entry (RU) and exit (EU) — TSPU
sees the raw TCP stream with MTProto patterns on the RU → EU international link.

### Production finding

Production infrastructure **never** sends raw proxy traffic on the RU → EU segment.
All entry-to-exit traffic is wrapped in VLESS Reality or XHTTP-TLS:

- **VLESS Reality**: Entry terminates Reality from the client, then opens a new
  VLESS Reality connection to the exit server. TSPU sees a TLS connection from RU
  to EU — standard HTTPS.
- **XHTTP-TLS**: Traffic is wrapped in HTTP/2 over TLS, with realistic API paths
  (e.g., `/api/v1/region/eu/`). TSPU sees HTTPS with plausible API patterns.

### Why this matters

TSPU inspects international traffic more aggressively than domestic. The RU → EU
link is where MTProto traffic is most vulnerable to:
- Statistical fingerprinting (packet size distribution, timing)
- Active probing (TSPU connects to exit IP:port and tests)
- Post-handshake payload analysis (MTProto Application Data)

An encrypted Reality/XHTTP wrapper makes the entry → exit segment look like
standard HTTPS traffic.

### Proposed change

This is a significant architecture change — replace `freedom` redirect with a
VLESS Reality or XHTTP-TLS outbound on the entry server. This requires:
1. Running an Xray instance on the exit server (in addition to telemt) to terminate
   the VLESS Reality connection
2. Xray on exit forwards decrypted MTProto to telemt on localhost
3. Updated deploy scripts for both entry and exit servers

Consider as a future architecture enhancement (ADR-level change).

## Pattern 4: Angie SNI Routing on Shared Servers

### Current template

The exit server `docker-compose.yml` runs telemt in a bridge network with
`ports: "443:443"`. If telemt shares a server with another proxy service (common
for cost optimization), port 443 conflicts.

### Production finding

Production infrastructure routinely runs multiple proxy protocols on a single server
using Angie (nginx fork) SNI stream routing:

```
:443 TCP → Angie stream (ssl_preread on, no decryption)
  ├─ SNI=domain-a.example.com → 127.0.0.1:8445 (service A)
  ├─ SNI=domain-b.example.com → 127.0.0.1:8443 (service B)
  └─ default → 127.0.0.1:8443
```

Angie reads only the SNI field from the TLS ClientHello (no decryption, no
certificate handling) and routes the raw TCP stream to the appropriate backend.
This allows multiple TLS-based services to share port 443 on one IP.

### Proposed change

Add an optional Angie SNI routing template to `infra/exit/` for shared-server
deployments. The current standalone template (telemt owns :443) remains the default.

## Pattern 5: Russian Datacenter Preference for Entry Servers

### Current template

`deploy-entry.sh` and README do not differentiate between Russian datacenter
providers. Any RU VPS is assumed equivalent.

### Production finding

Production experience indicates that TSPU applies less aggressive filtering to
certain Russian datacenter providers:

| Provider type | TSPU filtering intensity | Notes |
|---|---|---|
| Beget (RU) | Low | Russian-owned, popular hosting |
| Selectel (RU) | Low | Russian-owned, datacenters in MSK/SPB |
| Yandex Cloud (RU) | Low | Russian cloud, domestic IPs |
| Generic RU VPS providers | Variable | Depends on AS and IP reputation |

This is not a hard rule — TSPU filtering varies by region and ISP. But Russian-owned
datacenter providers with domestic ASNs are observed to have fewer false-positive
blocks than international providers' Russian PoPs.

### Proposed change

Update README and `deploy-entry.sh` to recommend Beget, Selectel, or Yandex Cloud
for the entry server. Add a note that the entry server's ASN should be a Russian ASN
to minimize geographic anomaly flags.

## Pattern 6: Realistic XHTTP Paths

### Current template

Not directly applicable — telemt entry uses `freedom` redirect, not XHTTP.

### Production finding

Production infrastructure using XHTTP-TLS for entry-to-exit or client-to-entry
segments uses **realistic API paths** rather than random strings:

| Path pattern | Example |
|---|---|
| `/api/v1/region/<cc>/` | `/api/v1/region/eu/` |
| `/api/v2/sync/` | `/api/v2/sync/` |
| `/api/v1/stream/` | `/api/v1/stream/` |

Random paths like `/d7x9Km2p` are technically valid but visually distinguishable
from real API traffic. Realistic paths blend into the ambient HTTPS noise.

If Pattern 3 (encrypted entry → exit via XHTTP) is adopted, use these path patterns
in the Xray config.

## Summary: Priority Matrix

| # | Pattern | Impact | Effort | Priority |
|---|---|---|---|---|
| 1 | Russian Reality SNI | High | Low (config change) | P0 |
| 2 | PROXYv1 instead of v2 | Medium | Low (config change) | P1 |
| 3 | Encrypted entry → exit | High | High (architecture) | P2 (ADR) |
| 4 | Angie SNI routing template | Medium | Medium (new template) | P1 |
| 5 | RU datacenter recommendation | Low | Low (docs) | P1 |
| 6 | Realistic XHTTP paths | Low | Low (config, if P3 adopted) | P2 |

## Relationship to Existing Knowledge Base

- `TELEMT_FAKETLS_DOMAIN_SELECTION_REPORT.md` — covers `tls_domain` and Reality SNI
  selection theory. This document adds production validation for Russian SNI choices.
- `TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md` — covers TSPU detection vectors. This
  document adds practical patterns that address those vectors.
- `TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md` — covers deploy hardening.
  Pattern 4 (Angie SNI routing) complements the shared-server deployment scenario.
