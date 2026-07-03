# FakeTLS Domain Selection for MTProxy Double-Hop Architecture — Path-Dependent TSPU Evasion

**Last updated: July 2026**

---

## Bottom Line: What to Change Right Now

The current template defaults are functional but carry three concrete risks that have triggered real blocking in 2026: `yahoo.com` as Reality SNI presents a foreign ASN to Russian DPI; `github.com` as `tls_domain` has an ASN mismatch against typical EU hosting (Azure AS8075 vs Hetzner AS24940) that MegaFon's A-record cross-check has already acted on [1]; and PROXYv2's 12-byte binary signature (`0x0D0A0D0A000D0A515549540A`) appears before the TLS ClientHello, creating a non-HTTPS-shaped byte sequence that any DPI pattern match can trivially flag [2]. The `freedom` redirect on the entry→exit segment exposes raw MTProto byte patterns to the RU→EU international gateway, where TSPU scrutiny is deepest.

The single architectural insight that supersedes all individual domain choices: **domain/SNI selection is not a global parameter — it must be optimised per segment**, because (RU ISP → entry) faces domestic DPI with Russian CDN whitelist enforcement, (entry → exit) faces the international gateway with the deepest inspection, and (exit → Telegram DCs) is outside Russia entirely and faces no TSPU scrutiny.

The April 1, 2026 detection event — TSPU fingerprinting the Telegram client TLS ClientHello via ECH extension and cipher suite ordering — and the June 5, 2026 JA4/JA4+ ban on Telegram ClientHello patterns [3] are the most significant recent changes. Both are mitigated by telemt's `tls_emulation`, which fetches real ServerHello from the SNI target and emulates it accurately [4]. Cloudflare-hosted domains have been throttled to 16 KB per connection in Russia since June 9, 2025 [5], eliminating an entire class of FakeTLS candidates.

**Change this now:**

| Parameter            | Current default     | Recommended value                                         | Segment | Reason                                                                                              |
| -------------------- | ------------------- | --------------------------------------------------------- | ------- | --------------------------------------------------------------------------------------------------- |
| `REALITY_SNI`        | `yahoo.com`         | `ads.x5.ru` (primary) + `ya.ru` (secondary)               | S1      | Russian CDN domains blend with domestic HTTPS; foreign domains trigger geographic anomaly detection |
| `tls_domain`         | `github.com`        | Self-steal domain (operator-owned) or `www.microsoft.com` | S2/S3   | ASN mismatch confirmed to trigger MegaFon blocking [1]; self-steal eliminates the vector entirely   |
| `proxyProtocol`      | `2` (PROXYv2)       | `1` (PROXYv1)                                             | S2      | PROXYv2 binary signature is trivially fingerprintable by DPI [2]                                    |
| Entry→Exit transport | `freedom` (raw TCP) | Encrypted VLESS-Reality tunnel                            | S2      | Raw TCP exposes MTProto patterns to international gateway DPI                                       |

---

## Section 1 — Reality SNI Selection for the RU Entry Server (Segment S1)

### Selection Criteria

A Reality SNI domain is used by Xray to fetch a real TLS ServerHello from `dest`, which it then presents to the client. TSPU sees the SNI in the ClientHello and cross-checks it against the server's IP via DNS A-record lookup. A domain fails this check if its A-record resolves to a different IP than the entry server — a confirmed blocking trigger [1]. Beyond the A-record check, TSPU's June 2026 "Siberian" behavioral module flags connections when three signals coincide: (1) the server IP is in a suspicious subnet (Selectel and Yandex.Cloud are specifically flagged), (2) the TLS fingerprint matches a proxy tool profile (Chrome became highly suspicious post-June 2026), and (3) more than 3 parallel TLS handshakes to the same SNI occur within a 60-second window with inter-connection delays under 350–400 ms.

Criteria for a viable Reality SNI domain:

- **Russian A-record**: the domain must resolve to a Russian IP, or at minimum a CDN with a confirmed Russian PoP, so the A-record cross-check passes when the entry server is in a Russian DC.
- **Not RKN-blocked**: the domain must be accessible from Russian ISPs.
- **TLS 1.3 with stable ServerHello**: Reality fetches the real ServerHello from `dest`; domains that change TLS config frequently or use non-standard setups break Reality's handshake cache.
- **High organic traffic**: the domain should carry significant legitimate HTTPS traffic so proxy connections blend into the noise.
- **TSPU whitelist presence**: Russian mobile internet whitelist databases (hxehex/russia-mobile-internet-whitelist, igareck/vpn-configs-for-russia) track which domains are treated as "approved" by TSPU during mobile internet restrictions. Whitelist presence is a positive signal.
- **Non-Chrome-suspicious ASN**: since June 2026, Selectel and Yandex.Cloud subnets are flagged as Signal 1. If your entry server is on Selectel, using a Selectel-hosted SNI domain actually increases Signal 1 correlation. Use a domain whose CDN ASN differs from your entry server's hosting ASN.

### Validation of Production-Claimed Domains

**`ads.x5.ru`** (X5 retail Group CDN): Present in the igareck/vpn-configs-for-russia WHITE-SNI-RU-all.txt whitelist with 6 occurrences as of July 3, 2026 — the highest frequency of any single domain in that file. Also appears in the VLESS-Reality mobile whitelist dated March 2026 with 150 domains. However, it is **not** present in the hxehex/russia-mobile-internet-whitelist. The discrepancy between the two lists is real: igareck tracks active production VLESS-Reality configs, while hxehex tracks the official state mobile whitelist. For Reality SNI purposes, the igareck list is more directly relevant — it shows which domains are actually deployed and working in production. One production config explicitly tags `ads.x5.ru` for Beeline mobile with IP `78.159.247.177`. **Assessment: Tier 1 candidate. Cross-validated in production configs; no blocking reports as of July 2026.**

**`sun6-21.userapi.com`** (VK/Mail.ru Group CDN): Present in hxehex whitelist but absent from igareck production configs. Netify.ai infrastructure data shows this hostname resolves to a VK network IP in the **Netherlands**, not Russia. This is a significant problem: if the A-record resolves to a Netherlands IP and your entry server is in Russia, TSPU's A-record cross-check will see a geographic mismatch. **Assessment: Tier 2 — whitelist-present but Dutch IP resolution is a latent risk. Use only if you verify the A-record resolves to a Russian IP from your entry server's perspective.**

**`avatars.mds.yandex.net`** (Yandex CDN): Present in hxehex whitelist, absent from igareck production configs. Yandex MDS (Media Data Storage) CDN is a high-traffic Russian infrastructure domain with stable TLS 1.3. Yandex infrastructure is generally TSPU-whitelisted. **Assessment: Tier 2 — good candidate, but lower production validation than `ads.x5.ru`. Worth including as a secondary `serverNames` entry.**

### Top-10 Reality SNI Candidates

| #   | Domain                   | ASN/Provider        | Russian PoP | TLS 1.3 stable | Traffic volume    | TSPU whitelist status        | Notes                                                     |
| --- | ------------------------ | ------------------- | ----------- | -------------- | ----------------- | ---------------------------- | --------------------------------------------------------- |
| 1   | `ads.x5.ru`              | X5 Retail CDN       | Yes (RU)    | Yes            | High (retail CDN) | igareck: Yes; hxehex: No     | 6 production occurrences Jul 2026; Beeline-validated      |
| 2   | `ya.ru`                  | Yandex (AS13238)    | Yes (RU)    | Yes            | Very high         | igareck: Yes                 | Xray community-recommended; Yandex core domain            |
| 3   | `avatars.mds.yandex.net` | Yandex MDS CDN      | Yes (RU)    | Yes            | Very high         | hxehex: Yes                  | High-traffic CDN; stable TLS config                       |
| 4   | `max.ru`                 | VK/Mail.ru          | Yes (RU)    | Yes            | High              | igareck: Yes (4 occurrences) | Streaming platform; high traffic                          |
| 5   | `api.ok.ru`              | OK.ru/VK CDN        | Yes (RU)    | Yes            | High              | igareck: Yes                 | Social media API endpoint; stable                         |
| 6   | `www.kinopoisk.ru`       | Yandex (AS13238)    | Yes (RU)    | Yes            | High              | igareck: Yes                 | Yandex-owned; high organic traffic                        |
| 7   | `storage.yandex.net`     | Yandex CDN          | Yes (RU)    | Yes            | Very high         | igareck: Yes (2 occurrences) | Object storage CDN; stable TLS                            |
| 8   | `stats.vk-portal.net`    | VK CDN              | Yes (RU)    | Yes            | Medium-high       | igareck: Yes                 | Analytics endpoint; lower profile                         |
| 9   | `sun6-21.userapi.com`    | VK (Netherlands IP) | Uncertain   | Yes            | High              | hxehex: Yes                  | Verify A-record resolves to RU before using               |
| 10  | `vkvideo.ru`             | VK Video CDN        | Yes (RU)    | Yes            | High              | Production reports           | Video CDN; used in deploy-entry.sh as RU domestic SNI [6] |

**Note on `yahoo.com` (current default)**: Yahoo resolves to Akamai/Verizon Media CDN with no Russian PoP. The A-record cross-check will fail for any Russian-DC entry server. Replace immediately.

### Single vs Multiple `serverNames`

Xray Reality accepts an array of `serverNames`. Using 2–3 names from the **same provider/ASN cluster** provides resilience if one domain's TLS config changes without expanding the active probing surface significantly. If TSPU probes all listed names, a wider list increases exposure. Recommended: use `ads.x5.ru` as primary (`serverNames[0]`) and `ya.ru` or `storage.yandex.net` as secondary. Do not mix providers (e.g., don't combine Yandex and VK domains in the same list — if TSPU correlates SNI with ASN, different-ASN domains in the same list look anomalous).

### `dest` Configuration

`dest` is the address Xray connects to when fetching the real ServerHello. It should match `serverNames[0]` exactly — this is a Xray configuration requirement, not a TSPU detection vector [7]. The common misattribution that "SNI-dest mismatch triggers TSPU" is incorrect: TSPU does not see the `dest` connection directly. The requirement is that `dest` serves a valid TLS 1.3 ServerHello for the domain in `serverNames[0]`. Set `dest` to `ads.x5.ru:443` if `serverNames[0]` is `ads.x5.ru`.

### `fingerprint` Selection in July 2026

The `fingerprint` parameter controls which uTLS fingerprint Xray uses for the Reality handshake on S1. The April 1, 2026 detection event targeted the **Telegram client's own TLS ClientHello** fingerprint — not the Xray fingerprint. The June 2026 Siberian module specifically flags **Chrome** as a highly suspicious fingerprint (Signal 2). This means:

- **`firefox`**: remains the best default. Firefox is the most common browser fingerprint globally and on Russian networks; it is not flagged by the June 2026 Signal 2 heuristic.
- **`chrome`**: explicitly flagged as highly suspicious by the June 2026 TSPU behavioral module. Avoid as primary; may be usable as a rotation option if Chrome's JA4 hash is updated by the time you read this.
- **`safari`**: less common on Russian networks (lower iOS/macOS market share); potentially conspicuous by rarity.
- **`randomized`**: generates unpredictable JA4 hashes that may not match any real browser's known fingerprint, making the connection more anomalous, not less.

**Recommendation**: use `firefox` as the default. If you suspect active probing is targeting Firefox specifically, rotate to `safari` (not `chrome`) as a temporary measure. Do not use `randomized` — it defeats the purpose of fingerprint mimicry.

---

## Section 2 — FakeTLS Domain Selection for the EU Exit Server (Segments S2 and S3)

### Why S2 Matters for `tls_domain` Selection

When the entry→exit segment uses `freedom` (raw TCP), TSPU at the RU→EU international gateway sees the FakeTLS handshake directly: the SNI in the ClientHello, the ServerHello characteristics, and the post-handshake MTProto payload. This means `tls_domain` selection affects both S2 (the RU→EU link TSPU sees) and S3 (EU→Telegram, outside Russia). If the S2 segment is encrypted with VLESS-Reality (Section 5), TSPU sees only the outer VLESS-Reality handshake on S2, and `tls_domain` only matters for S3 — where there is no TSPU scrutiny at all. This is the strongest argument for encrypting S2.

### Validation of `github.com`

GitHub uses Microsoft Azure CDN (AS8075). A Hetzner exit server (AS24940) presents a confirmed ASN mismatch: the `tls_domain` A-record resolves to Azure, but the actual TCP connection comes from Hetzner. MegaFon has blocked connections specifically when this IP-to-domain consistency check fails [1]. No reports exist of TSPU blocking `github.com` FakeTLS by domain name specifically — the blocking mechanism is the IP mismatch, not the domain itself. `github.com` has stable TLS 1.3, high traffic volume, and no ECH (so `tls_emulation` works). **Verdict**: still functional on ISPs that don't perform A-record cross-checking, but the ASN mismatch is a latent risk that self-steal eliminates entirely. Treat as fallback, not primary.

### Cloudflare Throttling Impact

Since June 9, 2025, Russian ISPs throttle Cloudflare-protected services to 16 KB per connection [5]. This affects any `tls_domain` whose A-record resolves to Cloudflare IPs. Practically eliminated candidates include: `cdn.cloudflare.net`, `ajax.cloudflare.com`, `registry.npmjs.org` (Cloudflare-proxied), `pypi.org` (Cloudflare-proxied), `www.cloudflare.com`. Note that `github.com` itself is **not** affected — it uses Azure CDN, not Cloudflare [5].

If S2 is unencrypted, avoid any Cloudflare-hosted `tls_domain`. If S2 is encrypted (Section 5), the Cloudflare throttle does not affect the S2 segment, but it would still affect the `tls_emulation` fetch if the fetcher routes through a Russian path.

### Top-10 FakeTLS Domain Candidates

| #   | Domain                   | Hosting ASN        | TLS 1.3 stable | `tls_emulation` compatible | Cloudflare risk | TSPU block reports | Notes                                                     |
| --- | ------------------------ | ------------------ | -------------- | -------------------------- | --------------- | ------------------ | --------------------------------------------------------- |
| 1   | Self-steal domain        | Operator's own ASN | Yes            | Yes (fetches from self)    | None            | None               | Eliminates ASN mismatch; requires domain + cert setup     |
| 2   | `www.microsoft.com`      | Microsoft AS8075   | Yes            | Yes                        | None            | None               | High traffic; stable TLS; no ECH                          |
| 3   | `www.apple.com`          | Apple/Akamai       | Yes            | Yes                        | None            | None               | High traffic; stable TLS; no ECH                          |
| 4   | `dl.google.com`          | Google AS15169     | Yes            | Yes                        | None            | None               | Download CDN; very stable TLS config                      |
| 5   | `storage.googleapis.com` | Google AS15169     | Yes            | Yes                        | None            | None               | Object storage; stable; high traffic                      |
| 6   | `github.com`             | Microsoft AS8075   | Yes            | Yes                        | None            | None               | ASN mismatch risk on Hetzner; functional otherwise        |
| 7   | `www.twitch.tv`          | Amazon AS16509     | Yes            | Yes                        | None            | None               | High traffic; stable TLS; no ECH                          |
| 8   | `www.netflix.com`        | Netflix AS2906     | Yes            | Yes                        | None            | None               | Blocked in Russia but exit is EU-side; stable TLS         |
| 9   | `www.google.com`         | Google AS15169     | Yes            | Verify (ECH risk)          | None            | None               | ECH may be enabled; test `tls_emulation` before deploying |
| 10  | `registry.npmjs.org`     | Cloudflare AS13335 | Yes            | Yes                        | **High**        | None               | Avoid if S2 unencrypted; Cloudflare-proxied               |

**ECH note**: `www.google.com` and some Google properties have begun enabling ECH. If ECH is active, `tls_emulation` cannot fetch a standard ServerHello and will fall back to a default fake cert. Test before deploying: if telemt logs show "TLS-front fetch not ready within timeout" [8], the domain has ECH or a non-standard TLS config.

### Self-Steal Strategy — Implementation Guide

Self-steal is the production-grade approach: you register a domain (e.g., `cdn.yourdomain.com`), point its A-record to your exit server's IP, obtain a TLS certificate for it, and set `tls_domain = "cdn.yourdomain.com"`. telemt's `tls_emulation` then fetches the ServerHello from your own server — the A-record resolves to your server's IP, so the ASN is identical to the actual connection's ASN. TSPU's A-record cross-check passes by construction.

**DNS setup**:

- Exit server self-steal: `cdn.yourdomain.com` A-record → exit server IP (EU)
- Entry server self-steal (for Reality SNI): `entry.yourdomain.com` A-record → entry server IP (RU) — but note that for Reality SNI, the domain also needs to serve a valid TLS 1.3 ServerHello from `dest`, so the entry server must run a TLS service (Angie/nginx) on port 443 for this domain.

**TLS certificate**: obtain via Let's Encrypt/ACME for the self-steal domain. The exit server runs Angie/nginx serving the certificate on port 443 (or 8080 for `mask_host`). telemt's `tls_emulation` fetches from `localhost:443` or the domain itself.

**Angie configuration sketch** (exit server, self-steal domain serving HTTPS for `tls_emulation`):

```nginx
# Angie/nginx: serves TLS certificate for self-steal domain
# telemt fetches ServerHello from here via tls_emulation
server {
    listen 443 ssl;
    server_name cdn.yourdomain.com;
    ssl_certificate /etc/letsencrypt/live/cdn.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cdn.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.3;
    # Return a plausible-looking response to active probes
    location / {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

**telemt config.toml** (exit server):

```toml
[censorship]
tls_domain = "cdn.yourdomain.com"
tls_emulation = true
mask_host = "cdn.yourdomain.com"
mask_port = 443
mask_proxy_protocol = 1  # PROXYv1
```

**Pros**: eliminates ASN mismatch entirely; operator controls rotation (update DNS TTL, swap A-record, restart telemt in ~30 seconds); no dependency on third-party TLS config changes breaking `tls_emulation`.

**Cons**: domain registration cost (low); domain may be blocked if it becomes associated with proxy activity (mitigate by using a generic-looking domain name and rotating); requires DNS management overhead.

**Important**: set DNS TTL to 300 seconds (5 minutes) on the self-steal domain. This enables fast rotation: if TSPU blocks the domain, update the A-record to a new IP and the change propagates in 5 minutes.

---

## Section 3 — Path-Dependent Strategy Matrix

The core insight is that S1 and S2/S3 face different TSPU scrutiny and require different optimisation targets.

| Segment | Path                         | TSPU scrutiny                                             | Recommended domain/SNI                                                                             | Rationale                                                                                |
| ------- | ---------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **S1**  | RU ISP → Entry (RU DC)       | High (domestic DPI, active probing, A-record cross-check) | Russian CDN domain: `ads.x5.ru` + `ya.ru`                                                          | Blends with domestic HTTPS; A-record resolves to RU IP; whitelist-present                |
| **S2**  | Entry (RU DC) → Exit (EU DC) | High (international gateway, deepest DPI)                 | **Encrypted VLESS-Reality tunnel** (Section 5); if `freedom`: avoid Cloudflare-hosted `tls_domain` | MTProto patterns visible on raw TCP; encryption is the correct fix, not domain selection |
| **S3**  | Exit (EU DC) → Telegram DCs  | None (outside Russia)                                     | Self-steal domain or any stable global domain                                                      | No TSPU scrutiny; stability and `tls_emulation` compatibility are the only constraints   |

### RU Entry DC vs Non-RU Entry DC

If the entry server is in a Russian datacenter (Beget, Selectel), traffic originates from a Russian ASN. The A-record cross-check is active: TSPU compares the SNI's DNS A-record against the entry server's IP. Using a Russian CDN domain that resolves to a Russian IP is correct here — the ASN plausibility argument is at its strongest. If the entry server is outside Russia (e.g., a Russian-speaking operator using a non-RU entry), the A-record check still applies, but the SNI domain's A-record needs to resolve to an IP that is geographically consistent with the entry server's location. In this case, a global CDN domain (e.g., `www.microsoft.com`) may be more appropriate than a Russian CDN domain for S1.

**Note on Selectel/Yandex.Cloud subnets**: the June 2026 Siberian module explicitly flags these as Signal 1 (suspicious server subnet). If your entry server is on Selectel, this means Signal 1 is always active for your connections regardless of SNI choice. Mitigation: move entry server to a non-flagged RU provider (Beget, TimeWeb, reg.ru), or accept that evasion depends on keeping Signals 2 and 3 clean (use `firefox` fingerprint, keep connection parallelism under 3).

### Should Reality SNI and FakeTLS Domain Be the Same?

No. Using the same domain for both S1 (Reality SNI) and S2/S3 (FakeTLS `tls_domain`) creates a single point of failure: if TSPU blocks the domain, both segments fail simultaneously. Using different domains per segment means one can be rotated without affecting the other. Additionally, the optimal domain type differs per segment: Russian CDN domains are optimal for S1 (domestic traffic blend) while global CDN domains or self-steal domains are optimal for S3 (stability and `tls_emulation` compatibility).

---

## Section 4 — PROXY Protocol Decision Matrix (Segment S2)

### PROXYv2 Binary Signature as a Detection Vector

PROXYv2 sends a 12-byte binary signature `\x0D\x0A\x0D\x0A\x00\x0D\x0A\x51\x55\x49\x54\x0A` as the first bytes of the TCP stream, before the TLS ClientHello [2]. This creates a non-TLS-shaped byte sequence at the start of the connection — trivially detectable by any DPI system doing a simple byte-string match on the first packet. No public evidence confirms TSPU currently performs this specific pattern match for blocking decisions, but the binary signature is fingerprintable in principle and the TELEMT_TSPU_EVASION_PATTERNS.md in this repo rates PROXYv2 at 5/10 for TSPU evasion vs PROXYv1 at 8/10 [9]. PROXYv1 sends an ASCII line (`PROXY TCP4 <src_ip> <dst_ip> <src_port> <dst_port>\r\n`) which superficially resembles an HTTP header and is less distinctive.

### telemt PROXYv1 Support

telemt 3.4.22 supports both PROXYv1 and PROXYv2 with automatic version detection [10]. The `mask_proxy_protocol` parameter in `[censorship]` accepts: `0` (disabled), `1` (PROXYv1 text), `2` (PROXYv2 binary) [11]. This parameter is not present in the default `config.toml` template and must be added manually [12]. The incoming `proxy_protocol` parameter in `[server]` is boolean and auto-detects both versions when set to `true` [11].

**Critical constraint**: when `proxy_protocol = true` is set in `[server]`, telemt rejects all connections that do not carry a PROXY header — no mixed-mode support on a single listener [13]. This means if you enable PROXY protocol, all connections to that listener (including any direct connections) must carry a PROXY header. This is the expected behavior for a double-hop architecture where all traffic arrives from the entry server via Xray.

### Decision Matrix

| Mode                                | TSPU evasion impact                                        | telemt feature impact                                                                  | Recommendation                               |
| ----------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------- |
| No PROXY (`proxy_protocol = false`) | Best: no detectable pre-TLS bytes                          | Loses real client IP: `user_max_unique_ips`, per-IP quotas, IP-based logging all break | Use only if IP-based features are not needed |
| PROXYv1 (`mask_proxy_protocol = 1`) | Good: ASCII header, less distinctive than binary           | Full client IP restoration; all IP-based features work                                 | **Recommended default**                      |
| PROXYv2 (`mask_proxy_protocol = 2`) | Lower: 12-byte binary signature before TLS ClientHello [2] | Full client IP restoration; all IP-based features work                                 | Avoid; change from current template default  |

### Xray Config Change for PROXYv1

The current entry server template sets `proxyProtocol: 2` in the `freedom` outbound [14]. Change to `proxyProtocol: 1`:

```json
{
  "outbounds": [
    {
      "protocol": "freedom",
      "settings": {
        "domainStrategy": "AsIs",
        "redirect": "__EXIT_SERVER_IP__:443",
        "proxyProtocol": 1
      }
    }
  ]
}
```

If replacing `freedom` with VLESS-Reality (Section 5), use `xver: 1` in the VLESS stream settings to forward PROXYv1 headers.

---

## Section 5 — Encrypted Entry → Exit Architecture

### Why Encrypt S2

With `freedom` redirect, TSPU at the RU→EU international gateway sees: (1) the FakeTLS ClientHello with the `tls_domain` SNI, (2) the ServerHello characteristics, and (3) post-handshake MTProto payload patterns. The April 2026 and June 2026 detection waves both operate on this visible traffic. Wrapping S2 in VLESS-Reality makes the international gateway see only a VLESS-Reality handshake to a Russian CDN domain — indistinguishable from a legitimate HTTPS connection to that domain. MTProto patterns are completely hidden from S2.

### Architecture

```
Entry server (RU DC):
  Xray inbound: VLESS-Reality on :443 ← Telegram clients connect here
  Xray outbound: VLESS-Reality → Exit server:443 (encrypted S2)

Exit server (EU DC):
  Xray inbound: VLESS-Reality on :443 ← receives from entry server
  Xray outbound: freedom → telemt on localhost:8443 (with PROXYv1)
  telemt: listens on :8443 (internal only, not exposed)
  Angie: :443 → Xray (SNI routing) + :8080 → mask_host
```

### Port Conflict Resolution

telemt defaults to port 443. If Xray also runs on port 443 (for the VLESS-Reality inbound from the entry server), they conflict. Solutions in order of preference:

1. **Move telemt to :8443** (recommended): telemt listens internally on :8443, Xray forwards decrypted traffic there. Port 8443 is not exposed externally.
2. **Xray fallback**: Xray on :443 handles Reality, falls back to telemt on localhost for non-Reality traffic [15]. More complex; requires Xray fallback configuration.

### Xray Outbound Config on Entry Server (Replacing `freedom`)

```json
{
  "outbounds": [
    {
      "tag": "exit-relay",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "EXIT_SERVER_IP",
            "port": 443,
            "users": [
              {
                "id": "EXIT_UUID",
                "encryption": "none",
                "flow": "xtls-rprx-vision"
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "SELF_STEAL_DOMAIN_OR_GLOBAL_CDN",
          "fingerprint": "firefox",
          "shortId": "EXIT_SHORT_ID",
          "publicKey": "EXIT_PUBLIC_KEY"
        }
      }
    }
  ]
}
```

This requires Xray running on the exit server with a matching VLESS-Reality inbound. The exit server's Xray then forwards decrypted traffic to telemt on `localhost:8443` via a `freedom` outbound with `proxyProtocol: 1`.

### Latency Overhead

The additional VLESS-Reality handshake adds 1–3 RTT for connection setup. For RU→EU links (typically 40–80 ms RTT), this is an 80–240 ms one-time overhead per new connection. For persistent MTProxy connections (Telegram maintains long-lived connections), this cost is paid once. The per-packet overhead is negligible. One source estimates the total overhead at 15–25 ms on sustained throughput for XHTTP-based transport. This is acceptable for Telegram messaging use.

### Is This Overkill?

If your current `freedom`-based deployment passes TSPU without issues, encrypting S2 is a defensive measure against future capability upgrades, not a fix for an active problem. The June 2026 TSPU wave specifically targeted post-handshake MTProto patterns on international links — if you're seeing blocking on S2, this is the fix. If not, implement it proactively: the June 2026 detection evolution shows TSPU is actively expanding its international gateway inspection capabilities. Production systems with Russian DC entry servers use encrypted S2 [9].

---

## Section 6 — TSPU Detection Evolution: July 2026 State

### Two Distinct 2026 Detection Waves

**Wave 1 — April 1, 2026**: TSPU identified a detection method for MTProxy FakeTLS based on the ECH extension presence, cipher suite ordering anomalies, and a unique JA3/JA4 fingerprint characteristic of Telegram's MTProxy implementation that does not match any modern browser [4]. Proxies using default FakeTLS without `tls_emulation` were blocked. telemt's `tls_emulation` (which fetches real ServerHello from the SNI target and emulates its TLS characteristics) directly mitigates this: it adjusts ECH extension handling and cipher suite ordering to match the target domain's actual browser-like behavior [4].

**Wave 2 — June 5, 2026**: Telegram client TLS ClientHello patterns were banned by JA4/JA4+ fingerprinting [3]. This is a separate event from Wave 1: Wave 1 targeted the FakeTLS handshake (server-side, controlled by telemt), while Wave 2 targeted the Telegram client's own ClientHello (client-side, controlled by the Telegram app). The telemt FAQ documents both events separately. Wave 2 is mitigated by updated Telegram clients; operators cannot directly fix it on the server side beyond ensuring `tls_emulation` is active.

The two events are sometimes reported with different dates in different sources (April 1 vs June 5). They are distinct events: April 1 targeted the proxy's FakeTLS handshake; June 5 targeted the Telegram client's native TLS fingerprint.

### June 2026 "Siberian" Behavioral Module

TSPU deployed a behavioral analysis module in June 2026 that triggers a 120-second connection freeze when three signals coincide (logical AND) [9]:

- **Signal 1 — Suspicious server subnet**: server IP is in a flagged ASN (Selectel, Yandex.Cloud confirmed; other VPS providers may be added over time).
- **Signal 2 — Suspicious TLS fingerprint**: ClientHello matches known proxy tool profiles; Chrome became highly suspicious post-June 2026.
- **Signal 3 — Connection burst**: more than 3 parallel TLS handshakes to the same SNI within a 60-second window with inter-connection delays under 350–400 ms.

All three must coincide for blocking to trigger. This means if your entry server is on a non-flagged ASN (Signal 1 absent), the other two signals alone are insufficient. The 120-second freeze doubles to 600 seconds if the client changes its TLS fingerprint while the freeze is active — meaning fingerprint rotation during a detection event makes things worse, not better.

TSPU performs full TCP stream reassembly before computing JA4 hashes, making single-packet fragmentation (MSS clamping) ineffective on nodes that perform reassembly. Blocking manifests as silent packet drops after the TLS handshake completes when MTProto Application Data begins — not TCP resets — resulting in a ~30-second timeout rather than an immediate connection error.

### AI/ML Detection Claims

Russia allocated approximately 2.27 billion rubles for an AI-powered internet censorship system planned for 2026 launch. The behavioral analysis described above (three-signal AND framework) is consistent with ML-based classification. However, the specific claim "AI Identifies MTProto Proxies" circulating in community channels is not corroborated by a credible technical source as of July 2026. The documented TSPU capabilities — JA4 fingerprinting, TCP stream reassembly, A-record cross-checking, behavioral burst detection — are all achievable with rule-based DPI without ML. **Assessment**: budget allocation and behavioral analysis suggest ML capability is being developed or deployed, but no public technical evidence confirms active ML-based MTProto classification as of this writing. Do not inflate the threat model based on this claim; the documented rule-based vectors are sufficient to explain observed blocking.

### Active Probing

TSPU's active probing workflow: detect suspicious traffic pattern → record IP:port → initiate its own connection to that address → send VPN handshake packets → analyze server response → add to blocklist if the server responds like a VPN. This is relevant for Reality SNI selection: the `dest` server (from which Reality fetches the ServerHello) must respond correctly to non-Reality connections. Using a real high-traffic domain as `dest` means TSPU probes will receive a legitimate TLS response, not a VPN fingerprint. Self-steal domains must also serve a plausible HTTPS response (the Angie config above returns `200 OK` for any path, which is sufficient).

### Per-ISP Differences

TSPU blocking is uneven per routing node, not uniformly per ISP. Beeline, MTS, MegaFon, and Rostelecom have all reported mixed results (both working and failing paths) due to uneven TSPU reassembly rollout. MegaFon has the most documented cases of A-record cross-check enforcement [1]. Tele2 and some regional ISPs tend to have less aggressive filtering, likely because TSPU hardware deployment is less complete on their networks.

**Operational implication**: optimise for MegaFon/Rostelecom as the baseline (A-record cross-check active, JA4 fingerprinting active, behavioral analysis active). If configurations work on MegaFon, they will work on less aggressive ISPs. Do not test only on Tele2 and assume it works everywhere.

### Post-Handshake Payload Analysis

TSPU detects MTProto traffic inside FakeTLS based on payload analysis after the TLS connection is established. This is a documented capability separate from handshake fingerprinting. It means that even with a perfect TLS handshake emulation, if the post-handshake payload contains detectable MTProto byte patterns, blocking can occur. This is the primary argument for encrypting S2: wrapping MTProto in VLESS-Reality makes the post-handshake payload opaque to TSPU.

---

## Section 7 — Telemt 3.4.22 Feature Compatibility

### PROXYv1 Support

Confirmed: telemt 3.4.22 supports PROXYv1 via `mask_proxy_protocol = 1` in the `[censorship]` section [11]. Automatic version detection for incoming connections is enabled by `proxy_protocol = true` in `[server]` [10]. The parameter is not present in the default `config.toml` and must be added manually [12].

Complete relevant config block:

```toml
[server]
proxy_protocol = true  # enables incoming PROXY header parsing (v1 or v2 auto-detected)
# proxy_protocol_trusted_cidrs = ["10.0.0.0/8"]  # optional: restrict who may send PROXY headers

[censorship]
tls_domain = "cdn.yourdomain.com"
tls_emulation = true
mask_host = "cdn.yourdomain.com"
mask_port = 443
mask_proxy_protocol = 1  # outgoing: PROXYv1 text-based
```

### `tls_emulation` Compatibility and Failure Modes

`tls_emulation` is enabled by default in telemt [12]. It fetches the real ServerHello from `mask_host:mask_port` at startup and caches it, then emulates the TLS record lengths and characteristics to match the target domain.

**Known failure modes**:

- **ECH-enabled domains**: if `mask_host` has ECH active, `tls_emulation` cannot complete a standard TLS handshake and falls back to a default fake cert. `www.google.com` and some Google properties are at risk. Test before deploying.
- **SOCKS5 upstream routing bug** (pre-v3.4.0): `tls_emulation` failed with `early eof` / `tls handshake eof` when the TLS fetcher routed through a SOCKS5 upstream instead of connecting directly [16]. Fixed in telemt v3.4.0. In 3.4.22, the `tls_fetch_scope` workaround is not required unless you have a non-standard upstream configuration.
- **15-second fetch timeout**: if `mask_host:mask_port` is not directly reachable during the TLS fetch phase (e.g., routed through an upstream that cannot reach the target), telemt times out and falls back to a cached/default cert [8]. Ensure `mask_host` is directly reachable from the exit server during startup.
- **Non-standard TLS configurations**: domains using TLS session resumption tickets in unusual ways, or domains that serve different ServerHello depending on client IP, may produce inconsistent `tls_emulation` behavior. High-traffic CDN domains (Microsoft, Apple, Google) have the most stable TLS configurations.

If you use a self-steal domain as `mask_host`, the fetch goes to `localhost:443` (or the domain's A-record, which resolves to your own IP). This is the most reliable configuration: you control the TLS config, ECH is not enabled, and the fetch always succeeds.

### Reverse Proxy Compatibility (Angie/nginx)

telemt can run behind Angie/nginx that terminates TLS for `mask_host` serving. The architecture is:

- Angie on `:8080` (or `:443` via SNI routing) serves the `mask_host` website with a real TLS certificate.
- telemt on `:443` handles MTProto/FakeTLS directly.
- telemt's FakeTLS operates on the MTProto layer; the Angie TLS termination for `mask_host` is independent.

FakeTLS still works when telemt is behind a reverse proxy, because FakeTLS is telemt's own TLS-like layer for MTProto traffic — it is not terminated by the reverse proxy. The reverse proxy only handles traffic directed at `mask_host`.

### `mask_host` on :443 vs :8080

| Configuration                                         | Setup                                            | Complexity | Notes                                                             |
| ----------------------------------------------------- | ------------------------------------------------ | ---------- | ----------------------------------------------------------------- |
| telemt on :443, Angie on :8080 (current template)       | Simple; no port conflict                         | Low        | Standard; Angie serves mask_host on non-standard port             |
| Angie on :443 with SNI routing to telemt               | Angie routes MTProto to telemt on :8443           | Medium     | More realistic (mask_host on standard port); requires SNI routing |
| Xray on :443 + telemt on :8443 (encrypted architecture) | Xray handles Reality inbound; forwards to telemt | High       | Required if implementing Section 5                                |

**Recommendation**: if implementing encrypted S2 (Section 5), Xray must own :443 on the exit server. Move telemt to :8443 (internal) and Angie to :8080 for mask_host. If not implementing encrypted S2, the current template (telemt on :443, Angie on :8080) is the simplest configuration.

---

## Section 8 — Operational Runbook: Rotation, Monitoring, and Fallback

### Domain Rotation Strategy

TSPU behavioral detection can learn domain-specific patterns over time if the same domain is used persistently with high connection volume. The documented blocking waves targeted specific fingerprints, not specific domains, but domain-level blocking is possible if a domain becomes associated with proxy activity in TSPU's correlation data.

**Rotation schedule**:

- Proactive rotation: every 30–90 days for `tls_domain`; every 60–120 days for `REALITY_SNI` (less frequent because SNI changes require Xray restart and Reality key renegotiation).
- Reactive rotation: immediately upon detecting ISP-specific failures (see monitoring below).

**Self-steal domains**: rotation requires updating the DNS A-record to a new server IP and updating `tls_domain` in `config.toml`. With TTL=300s, propagation takes ~5 minutes. Total downtime: ~30 seconds (telemt restart) + ~5 minutes (DNS propagation) = under 6 minutes.

**Third-party domains** (github.com, etc.): rotation requires only updating `tls_domain` in `config.toml` and restarting telemt (~30 seconds). No DNS control needed, but you cannot change the A-record to match your server IP.

### Monitoring Strategy

Effective monitoring requires PROXY protocol enabled (so telemt can see real client IPs and segment by ISP):

- **Connection success rate by ISP**: segment telemt connection logs by source IP → ISP (via ASN lookup). A drop in success rate for MegaFon clients while Tele2 clients succeed indicates TSPU filtering, not a server issue.
- **Latency spikes on S1**: sudden RTT increases on the entry server's :443 without corresponding CPU/bandwidth increases indicate TSPU throttling (not blocking).
- **`tls_emulation` health**: telemt logs "TLS-front fetch not ready within timeout" when the ServerHello fetch fails. Monitor for this log line — it indicates either the `mask_host` domain has changed its TLS config or ECH has been enabled.
- **Active probing detection**: unexpected connections to the entry server's :443 that complete the TLS handshake but do not send valid MTProto data. These are TSPU probes. Log and alert on connections that complete TLS but produce no MTProto traffic within 5 seconds.
- **Post-ban IP range exposure**: TSPU bans can hit neighboring IPs in the same subnet. If one proxy IP is banned, check adjacent IPs for increased probe traffic.

### Fallback Configuration

telemt does not natively support multiple `tls_domain` values with automatic failover. Operational approach:

1. Maintain a list of 3–5 pre-validated backup domains in the deploy script (tested for TLS 1.3 stability and no ECH).
2. On detection of blocking: update `tls_domain` in `config.toml`, restart telemt (~30 seconds downtime).
3. For self-steal domains: pre-provision backup domains with DNS A-records already pointing to the exit server. Switching is a single config line change.

**Impact of domain blocking**: if TSPU blocks the `tls_domain`, clients fail at the FakeTLS handshake. The proxy server continues running. Recovery time with a pre-validated backup: ~30 seconds. If `REALITY_SNI` is blocked, connections fail; update `serverNames` in Xray config and restart Xray (~10 seconds).

---

## Section 9 — Recommended Changes for the telemt-mgmt Repo

| File                                    | Parameter                             | Current value | Proposed value                                                | Rationale                                                         |
| --------------------------------------- | ------------------------------------- | ------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| `infra/entry/xray-config.json.template` | `REALITY_SNI` (in `serverNames`)      | `yahoo.com`   | `ads.x5.ru`                                                   | Cross-validated Russian CDN domain; production-deployed July 2026 |
| `infra/entry/xray-config.json.template` | `serverNames`                         | Single value  | `["ads.x5.ru", "ya.ru"]`                                      | Resilience against single-domain TLS config changes               |
| `infra/entry/xray-config.json.template` | `proxyProtocol` (in freedom outbound) | `2`           | `1`                                                           | PROXYv2 binary signature is fingerprintable [2]                   |
| `infra/entry/xray-config.json.template` | `fingerprint`                         | `firefox`     | `firefox`                                                     | Keep; Chrome is now flagged by June 2026 TSPU behavioral module   |
| `infra/exit/config.toml.template`       | `tls_domain`                          | `github.com`  | `${SELF_STEAL_DOMAIN}` (with fallback to `www.microsoft.com`) | ASN mismatch risk; self-steal preferred                           |
| `infra/exit/config.toml.template`       | `mask_proxy_protocol`                 | (not set)     | `1`                                                           | Explicit PROXYv1; must be added to `[censorship]` section         |

**Additional recommendations**:

1. **Add `SELF_STEAL_DOMAIN` template variable** to both entry and exit templates, with documentation explaining the DNS A-record setup and Let's Encrypt certificate acquisition. Make it optional with a fallback to a third-party domain.

2. **Add `docs/knowledge/DOMAIN_ROTATION_LOG.md`** template with fields: date, old domain, new domain, reason for rotation, ISPs affected. Operators should commit rotation events so the team can correlate blocking patterns over time.

3. **Add connectivity check to deploy scripts**: after deployment, run a basic connectivity test from a RU VPS (or use a RU residential IP via a test Telegram client) to verify the proxy is reachable. A deploy that succeeds on the EU server but fails from Russia indicates TSPU blocking, not a configuration error.

4. **Document the Selectel/Yandex.Cloud subnet flag**: add a note to the deploy script warning that if the entry server is on Selectel or Yandex.Cloud, Signal 1 of the June 2026 behavioral module is always active, and operators should consider migrating to Beget, TimeWeb, or reg.ru for the entry server.

---

## Section 10 — Explore Further

**1. XHTTP transport for S2 as a VLESS-Reality alternative**: Xray's XHTTP transport (HTTP/2 or HTTP/3 framing) wraps traffic in standard HTTP request/response patterns, which may have different fingerprinting characteristics than VLESS-Reality's TLS-based approach. Community double-hop implementations use VLESS+XHTTP+Reality successfully. The latency profile differs: XHTTP's HTTP/2 multiplexing may reduce head-of-line blocking for Telegram's concurrent connection model. Research whether XHTTP's fingerprint is less recognizable than VLESS-Reality's on the RU→EU international link, and whether TSPU's June 2026 behavioral module has specific rules for XHTTP patterns.

**2. Telegram DC routing and TSPU filtering rules per DC**: telemt routes to Telegram's DC endpoints (DC1–DC5). TSPU may apply different filtering rules to traffic destined for different Telegram DC IP ranges — some DC ranges may be more aggressively monitored than others. Research whether routing through specific DCs (e.g., DC1 in Miami vs DC5 in Singapore) affects detection rates, and whether telemt's DC routing configuration can be used to prefer less-monitored DC endpoints.

**3. RKN blocklist monitoring integration into CI/CD**: the `hxehex/russia-mobile-internet-whitelist` and `igareck/vpn-configs-for-russia` repositories are community-maintained and updated frequently (the igareck list was updated July 3, 2026). Integrating a daily check into the repo's CI/CD pipeline — comparing current `REALITY_SNI` and `tls_domain` values against these lists — would provide early warning when a candidate domain disappears from whitelists or appears on RKN block lists. GitHub Actions can fetch the raw whitelist files and diff against configured values, triggering an alert if a configured domain is no longer present.

## References

[1] Telemt MTProxy v3.3.28 + AmneziaWG + HaProxy - not working #565. https://github.com/telemt/telemt/issues/565
[2] TSPU-IMC22: Russia's Internet Filtering Infrastructure. https://censoredplanet.org/papers/tspu-imc22.pdf
[3] Telemt - MTProxy on Rust + Tokio. https://github.com/telemt/telemt
[4] telemt/docs/FAQ.en.md at main - GitHub. https://github.com/telemt/telemt/blob/main/docs/FAQ.en.md
[5] Russian Internet users are unable to access the open Internet. https://blog.cloudflare.com/russian-internet-users-are-unable-to-access-the-open-internet/
[6] Current telemt-mgmt entry deploy script recommends vkvideo.ru for RU domestic Reality SNI, with yahoo.com as the default fallback. https://raw.githubusercontent.com/ponkcore/telemt-mgmt/main/infra/entry/deploy-entry.sh
[7] Xray-examples/VLESS-TCP-XTLS-Vision-REALITY. https://github.com/XTLS/Xray-examples/blob/main/VLESS-TCP-XTLS-Vision-REALITY/REALITY.ENG.md
[8] TLS fetch timeout is 15 seconds; mask_host:mask_port must be directly reachable during TLS fetch phase, not routed through default upstream. https://github.com/telemt/telemt/issues/722
[9] TSPU Evasion: Production-Proven Patterns for the Double-Hop Architecture (July 2026). https://raw.githubusercontent.com/ponkcore/telemt-mgmt/main/docs/knowledge/TELEMT_TSPU_EVASION_PATTERNS.md
[10] Support for PROXY protocol defined by HAProxy · Issue #631. https://github.com/telemt/telemt/issues/631
[11] telemt CONFIG_PARAMS.en.md Documentation. https://github.com/telemt/telemt/blob/main/docs/Config_params/CONFIG_PARAMS.en.md
[12] telemt config.toml. https://raw.githubusercontent.com/telemt/telemt/main/config.toml
[13] Per-listener proxy_protocol (or per-CIDR fallback) for mixed direct + .... https://github.com/telemt/telemt/issues/777
[14] Entry server Xray config template sets proxyProtocol to 2 (PROXYv2) in the freedom outbound to exit server. https://raw.githubusercontent.com/ponkcore/telemt-mgmt/main/infra/entry/xray-config.json.template
[15] Fallback - Project X. https://xtls.github.io/en/config/features/fallback.html
[16] TLS emulation fails with 'early eof' or 'tls handshake eof' errors when the TLS fetcher routes through SOCKS5 upstream instead of direct connection to local address. https://github.com/telemt/telemt/issues/330
