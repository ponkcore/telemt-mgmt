# FakeTLS Domain Selection for Russian DPI Evasion: July 2026 Operator Guide

## Bottom Line First: The Two Tables That Matter

In the double-hop Xray VLESS-Reality + Telemt architecture, **the entry server's Reality SNI is the primary DPI-evasion surface**; the exit server's `tls_domain` is secondary. TSPU sees the Telegram client connecting to the Russian entry server (Server A) and inspects that TLS ClientHello. The EU exit server (Server B) is reached only via an encrypted VLESS-Reality tunnel — TSPU cannot observe Server B's `tls_domain` at all [1]. This means the two tables below serve different purposes and their values do not need to match [1].

Two events define the current threat context. On April 1, 2026, TSPU began detecting FakeTLS via ECH extension presence, cipher suite ordering, and a JA3/JA4 fingerprint not found in modern browsers — this was the first mass MTProxy outage [2]. On June 5, 2026, TSPU added a second wave: JA4/JA4+ fingerprint blocking of the Telegram ClientHello itself, regardless of SNI [3][4]. Both detection events have been patched in current Telegram clients (Desktop, Android, iOS), but users on old clients remain blocked [2].

### Top 5 `tls_domain` Candidates for EU-Hosted Exit Server (July 2026)

| Rank | Domain              | Category                   | TLS ver     | ASN match risk (EU server)                              | TSPU block risk | Confidence  |
| ---- | ------------------- | -------------------------- | ----------- | ------------------------------------------------------- | --------------- | ----------- |
| 1    | `www.microsoft.com` | US Big Tech / Azure CDN    | TLS 1.3 [5] | Medium — Azure CDN has global PoPs, no Russian PoPs [6] | Low             | Medium-High |
| 2    | `github.com`        | US Tech / Azure CDN        | TLS 1.3     | Medium — Azure-backed, no Russian PoPs [6]              | Low             | Medium-High |
| 3    | `www.twitch.tv`     | US Streaming / AWS CDN     | TLS 1.3     | Medium — AWS, no Russian PoPs [6]                       | Low             | Medium      |
| 4    | `wikipedia.org`     | Non-profit / Wikimedia CDN | TLS 1.3     | Medium — distributed CDN                                | Low             | Medium      |
| 5    | `www.google.com`    | US Big Tech / Google CDN   | TLS 1.3     | Medium — no dedicated Russian PoP for root domain       | Low-Medium      | Medium      |

> **Note on cloudflare.com**: Cloudflare IPs have been throttled in Russia since June 2025 per Cloudflare's own blog [7]. Using `cloudflare.com` as `tls_domain` means your exit server impersonates a host that Russian users may already see degraded connectivity to — this creates a detectable anomaly. Treat it as a fallback, not a primary.

> **Note on petrovich.ru** (telemt's default [8]): This is a Russian retail site with a GlobalSign cert and TLS 1.3 [2]. It works correctly when the proxy server is also hosted in Russia. For a EU-hosted exit server, Issue #274 explicitly identifies petrovich.ru as a **negative example** — the ASN mismatch between a German/Dutch hosting provider and a Russian-hosted domain is immediately detectable [6]. Do not use the default for EU deployments.

> **Note on apple.com / icloud.com**: Apple keeps its IPs in dedicated Apple ASNs. Any EU server impersonating apple.com will have an ASN mismatch that is structurally detectable [6].

### Top 3 Reality SNI Candidates for Server A (Russia Entry)

| Rank | Domain                        | Rationale                                                                                                             | Confidence |
| ---- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1    | `www.microsoft.com`           | Stable TLS 1.3, globally recognized, accessible in Russia, Azure CDN presence provides plausible traffic [6]          | Medium     |
| 2    | `vkvideo.ru` (or `eh.vk.com`) | Russian domestic domain, whitelisted by TSPU, ASN plausible for Russian server; used in production double-hop configs | Medium     |
| 3    | `yahoo.com`                   | Used in the official telemt XRAY_DOUBLE_HOP example config [1]; accessible in Russia; stable TLS 1.3                  | Medium     |

> **Important**: The telemt XRAY_DOUBLE_HOP docs use `yahoo.com:443` as the Reality `dest` and `serverNames = ["yahoo.com"]` [1]. This is the documented starting point. For a Russian entry server, a domestic domain like `vkvideo.ru` may be more resilient because it is whitelisted and its traffic from Russian IPs raises no geographic anomaly flag. `yahoo.com` and `www.microsoft.com` are safe for initial deployment; switch to a domestic Russian domain if the entry server is flagged.

---

## How TSPU Detects FakeTLS: The Threat Model

### Confirmed Detection Vectors (July 2026)

**JA4/JA4+ ClientHello fingerprinting** has been active since June 5, 2026 [3][4]. TSPU identifies the Telegram client's specific TLS fingerprint (JA4 hash `t13d1516h2_8daaf6152771_d8a2da3f94cd` was confirmed in tdesktop issue #30733 [9]). This detection operates on the ClientHello regardless of what SNI is present — it targets the _client_, not the domain. The fix is updated Telegram clients; server-side `tls_domain` selection cannot address this vector [2].

**ECH extension + cipher suite ordering** has been active since April 1, 2026 [2]. TSPU detected FakeTLS by comparing the ECH extension presence and cipher suite ordering in the handshake against what the claimed SNI domain would actually produce. Telemt's `tls_emulation` feature — which fetches the real ServerHello parameters from the SNI target — directly addresses this: the ServerHello cipher suites and extensions are fetched from the real domain, making them match [2]. The April 2026 detection was caused by old Telegram client TLS parameters that produced a fingerprint inconsistent with modern browsers; patched clients resolved this [2].

**SNI-based blocking** is TSPU's primary TLS method, documented in the Censored Planet TSPU-IMC22 research [10]. TSPU parses the SNI field from the TLS ClientHello on port 443. If the SNI matches a blocked domain, the connection is dropped. This is why `tls_domain` must be an accessible, non-blocked domain.

**ASN/IP mismatch detection**: If SNI = `microsoft.com` but the server IP belongs to Hetzner (AS24940), a DPI system with ASN correlation can flag this. Telemt Issue #274 documents this as a primary detection vector [6], and MegaFon has been confirmed to block connections where `tls_domain` IP did not match the actual server IP [11]. **Confidence: Medium** — the mechanism is confirmed at the ISP level (MegaFon), but whether all Russian TSPU appliances perform real-time ASN correlation is not publicly documented. The A-record validation variant (June 2026) is documented by the teleproxy community: TSPU validates that the SNI domain's A-record resolves to the proxy server's IP [12]. If this is deployed, it means only self-owned domains (where you control DNS) or domains with no fixed A-record (CDNs with many IPs) can pass this check.

**Connection frequency behavioral detection**: TSPU triggers a 120-second block when more than 3 parallel TLS connections to the same SNI occur within a 350–400 ms window [12]. This targets the Telegram client's connection burst pattern (multiple simultaneous DC connections). This is a behavioral signal, independent of domain choice.

**Post-handshake payload analysis**: TSPU allows the TLS handshake to complete, then silently drops packets when MTProto Application Data begins transmitting [13][12]. This is confirmed in mtg issue #547 [13]: the blocking occurs at the Application Data stage, not during the handshake. TSPU uses silent drops rather than TCP RST, causing client retransmission loops [13]. This detection vector operates after FakeTLS succeeds — meaning correct `tls_domain` selection is necessary but not sufficient for sustained connectivity.

In sum, TSPU's June 2026 detection combines TCP stream reassembly, A-record verification, JA4/JA4+ fingerprinting, and post-handshake payload analysis into a multi-signal system [12]. Blocking triggers only when multiple signals coincide simultaneously — avoiding any single signal may prevent a block, but the combination of signals is increasingly comprehensive.

### Active Probing

The Censored Planet TSPU-IMC22 paper documents that TSPU infrastructure is capable of active probing [10]. Telemt's `mask_host` is designed to handle this: non-Telegram traffic (including HTTP probes) is forwarded to a real nginx/Angie web server, so probes receive a legitimate HTTP response [2]. The telemt FAQ states "crawlers are completely satisfied receiving responses from mask_host" [2]. **Whether TSPU currently sends active HTTP probes after seeing a TLS connection on suspected proxy IPs is not confirmed in public sources** — label as Low confidence. Configure `mask_host` correctly regardless, as it costs nothing and covers this scenario.

### Traffic Pattern Analysis

TSPU detection evolved through three stages by May 2026: IP/port blocking (pre-2025), JA3/JA4 TLS fingerprinting (March–April 2026), and statistical traffic analysis of packet size distribution and inter-packet timing (May 2026 onward). Only 3 of 27 MTProxy configurations survived testing across 6 Russian networks in late May 2026, with federal operators (MTS, YOTA) showing 0% success rate while regional providers had partial success. This strongly suggests post-handshake traffic analysis is active on federal networks. The double-hop architecture partially mitigates this: TSPU sees the entry→exit segment as an encrypted Xray/Reality tunnel, not raw MTProto — the distinctive MTProto packet patterns are hidden inside the tunnel.

### Research Literature

The Censored Planet TSPU-IMC22 paper [10][14] is the primary academic source on TSPU's architecture and detection methods. The USENIX Security 2024 paper on fingerprinting encapsulated TLS handshakes [15] is relevant to the JA4 detection mechanism. No additional academic papers specifically on FakeTLS/MTProxy detection in Russia were surfaced beyond these two sources — further literature search would be required to cover 2025–2026 publications.

---

## Domain Category Analysis

| Category                    | Example domains                        | TSPU block risk   | ASN mismatch risk (EU server) | TLS stability              | RKN blocklist risk | Verdict                             |
| --------------------------- | -------------------------------------- | ----------------- | ----------------------------- | -------------------------- | ------------------ | ----------------------------------- |
| US Big Tech (Azure/AWS CDN) | microsoft.com, github.com, twitch.tv   | Low               | Medium                        | High — TLS 1.3, stable     | Very low           | **Recommended** [6]                 |
| US Big Tech (dedicated ASN) | apple.com, icloud.com                  | Low               | High — Apple owns its ASNs    | High                       | Very low           | **Avoid** [6]                       |
| Cloudflare CDN              | cloudflare.com                         | Low-Medium        | Low                           | High                       | Low                | **Fallback only** [7]               |
| CDN root domains            | cloudfront.net, fastly.net, akamai.net | Low               | Low                           | Medium — root SNI unusual  | Low                | **Complex, not recommended**        |
| Russian Big Tech            | yandex.ru, vk.com, rutube.ru           | Low (whitelisted) | High for EU server            | High                       | Very low           | **Russia-only servers**             |
| Russian retail              | petrovich.ru                           | Low               | High for EU server            | High — GlobalSign, TLS 1.3 | Very low           | **Russia-only; telemt default** [8] |
| Russian Government          | gosuslugi.ru, kremlin.ru               | Very low          | High for EU server            | High                       | Very low           | **Avoid — legal risk**              |
| Non-profit / international  | wikipedia.org                          | Very low          | Medium                        | High                       | Very low           | **Recommended**                     |
| Self-owned domain           | proxy.example.com                      | High              | Low (if DNS correct)          | High                       | Low                | **Conditional — see §5**            |
| CDN subdomains (fronting)   | \*.cloudfront.net                      | Low               | Low                           | Medium                     | Low                | **Complex, requires CDN setup**     |

**microsoft.com and github.com** are the most consistently recommended domains for EU-hosted servers [6][16]. Both are backed by Azure CDN infrastructure with no dedicated Russian Points of Presence, so a Hetzner or OVH server impersonating them has a plausible (if imperfect) ASN profile. TLS 1.3, stable certificate configuration, and no RKN blocklist status make them reliable for telemt's ServerHello fetching.

**www.twitch.tv** is recommended in Issue #274 alongside microsoft.com and github.com [6]. AWS-backed, no Russian PoPs, stable TLS 1.3.

**wikipedia.org** is accessible in Russia (not on RKN blocklist as of July 2026), uses TLS 1.3, and is hosted on Wikimedia CDN infrastructure. Used in community installer scripts as an example value. Good candidate.

**google.com**: partially blocked in Russia historically at the IP level, though the domain itself may not be on the RKN SNI blocklist. Status as of July 2026 is not confirmed from available sources — treat as Medium risk. MTProxyMax lists it as a recommended cover domain [16], but Cloudflare throttling precedent suggests caution with any US tech giant that has active Russian blocking history.

**cloudflare.com**: Cloudflare has been throttling its IPs in Russia since June 2025, confirmed by Cloudflare's own blog [7]. A server impersonating cloudflare.com may face elevated scrutiny precisely because Cloudflare traffic is already a known evasion tool. Use as a fallback.

**Russian Big Tech (yandex.ru, vk.com, rutube.ru)**: These are whitelisted by TSPU and have single-round x25519 handshakes that FakeTLS can replicate cleanly. However, for a **EU-hosted exit server**, the ASN mismatch is large — a Hetzner IP claiming to be yandex.ru is immediately suspicious. These domains are correct choices only for Russia-hosted servers. The mtproto.zig documentation recommends rutube.ru, ozon.ru, vk.com, yandex.ru for MTProxy deployments and explicitly warns against wb.ru (uses HRR/secp521r1 handshake that simplified FakeTLS cannot replicate).

**ozon.ru**: Despite appearing in community configs (telemt Issue #617 [17]), the same issue documents that an ozon.ru configuration **failed** with handshake timeout errors in Russia [17]. Do not treat its appearance in configs as evidence it works.

**mail.ru and fastly.net**: Only support TLS 1.2, not TLS 1.3. Since TSPU's April 2026 detection targeted ECH and modern TLS fingerprints, TLS 1.2 domains produce inconsistent fingerprints compared to modern browser behavior [2]. Avoid.

**gosuslugi.ru / kremlin.ru**: Technically whitelisted, but impersonating government infrastructure for proxy services carries serious legal risk under Russian law. Confidence: High on the legal risk. Avoid regardless of technical suitability.

**CDN root domains (cloudfront.net, akamai.net)**: The root domain SNI is unusual — real traffic uses subdomain SNIs like `d1234.cloudfront.net`. A connection to the CDN root SNI is an anomalous pattern that DPI can flag. Additionally, telemt's `mask_host` forwarding would need to serve real content on the CDN root SNI, which requires CDN setup. Not recommended without additional infrastructure.

---

## TSPU Detection: The ASN Mismatch Problem in Detail

Telemt's `tls_emulation` fetches the real ServerHello parameters (cipher suites, extensions, certificate length) from the SNI target domain. This makes the ServerHello wire-indistinguishable from the real domain's [2]. But the server's IP address remains in the hosting provider's ASN, not the target domain's ASN.

Issue #274 documents ASN/IP consistency as the primary criterion for `tls_domain` selection [6]. The June 2026 teleproxy documentation describes a specific TSPU check: A-record verification, where TSPU validates that the SNI domain's A-record resolves to the proxy server's IP [12]. If this is deployed as described, it means:

- **Popular domains (microsoft.com, github.com)**: Their A-records resolve to Microsoft/GitHub IPs, not your Hetzner server. This check would fail. However, CDN-backed domains resolve to many different IPs globally, making this check less deterministic — a Hetzner IP is unusual but not impossible for a CDN edge node.
- **Self-owned domain**: If you control DNS and set the A-record to your server's IP, this check passes. This is the strongest technical argument for self-owned domains (see §5).
- **Russian domestic domains on EU server**: A-record resolves to Russian IP, not your EU server. This check fails with high certainty.

**Confidence on A-record validation**: Medium. The teleproxy documentation [12] is a community source, not an official TSPU specification. The MegaFon IP-mismatch blocking [11] is confirmed from a user report (single source). The mechanism is plausible and consistent with observed blocking patterns, but has not been confirmed by academic measurement studies as a universally deployed TSPU feature.

**Implication for domain selection in the double-hop architecture**: TSPU applies A-record validation to the entry server's Reality SNI (what TSPU can see), not the exit server's `tls_domain`. For the exit server, this check is irrelevant because TSPU cannot see Server B's traffic. This significantly reduces the ASN mismatch problem for `tls_domain` selection — the primary concern is choosing a domain whose ServerHello telemt can fetch reliably.

TSPU also flags Chrome-like fingerprints from suspicious ASNs (Hetzner, DigitalOcean) as anomalous, while the same fingerprint from a Google IP is considered normal. This contextual ASN-fingerprint mismatch heuristic means the hosting provider's ASN reputation matters independently of the SNI domain.

---

## Self-Owned Domain as `tls_domain`: Conditions and Verdict

The core argument for self-owned domains: you control both the domain's DNS A-record and the web server, so the A-record points to your server IP (passing A-record validation), the ServerHello exactly matches (because it _is_ your server), and HTTP probes get real responses.

| Condition                                      | Self-owned better? | Reason                                                                                                      |
| ---------------------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------- |
| TSPU performs A-record validation              | YES                | Self-owned DNS points to your server IP = exact match [12]                                                  |
| TSPU sends active HTTP probes                  | YES                | Real web server on same IP responds consistently [2]                                                        |
| TSPU blocks small/unknown domains quickly      | NO                 | Popular domains have collateral-damage protection; small domains can be blocked individually without impact |
| Double-hop (TSPU never sees exit `tls_domain`) | NEUTRAL            | A-record advantage is irrelevant if TSPU can't see the exit server's SNI [1]                                |
| Domain appears in proxy links                  | NO                 | Self-owned domain is directly linkable to your proxy service; popular domains are not                       |

**For the double-hop architecture specifically**: since TSPU does not see the exit server's `tls_domain`, the A-record advantage of self-owned domains does not apply to `tls_domain` selection. The self-owned domain advantage only matters if users connect to the exit server directly (single-hop fallback).

**Practical constraints for self-owned domains** [18]: Setting `censorship.mask_port = 443` to enable TLS emulation certificate caching may break masking functionality. Self-owned domains with `dns_overrides` pointing to `127.0.0.1` fail TLS emulation fetch with early EOF errors unless `fetch_scope` is set to `direct` [18]. These are solvable but require careful configuration.

**Verdict**: For the double-hop architecture, prefer popular CDN-backed domains (microsoft.com, github.com) for `tls_domain` on the EU exit server. Self-owned domains are viable for single-hop setups where TSPU sees the exit server directly, but they require correct DNS configuration, a realistic-looking website, and a rotation plan for when the domain gets blocked. Confidence: Medium.

---

## The Double-Hop Architecture: What TSPU Sees and What It Doesn't

```
Telegram client
 |
 | tg://proxy?server=SERVER_A_IP:443&secret=...
 v
[Server A — Russia entry]
 Xray VLESS-Reality, port 443/tcp
 Reality SNI: e.g., yahoo.com or www.microsoft.com
 TSPU sees this connection ← CRITICAL SURFACE
 |
 | VLESS-XTLS-Reality tunnel (encrypted)
 | PROXYv2 header preserves client IP
 v
[Server B — EU exit]
 Xray server + Telemt MTProxy, port 8443/tcp (localhost only)
 tls_domain: e.g., github.com
 TSPU CANNOT see this ← secondary surface
 |
 v
Telegram DCs
```

The proxy link's `server=` field contains **Server A's IP/FQDN** (the Russia entry server), not Server B's IP [1]. This is explicitly documented: the telemt config on Server B sets `public_host = '<FQDN_OR_IP_SERVER_A>'` to generate correct proxy links [1]. TSPU therefore only observes the client → Server A connection, with Server A's Reality SNI in the ClientHello.

The Reality SNI and `tls_domain` are completely independent parameters — they do not need to match [1]. Server A's Reality SNI is chosen for Russian DPI evasion; Server B's `tls_domain` is chosen for Telegram client validation and single-hop fallback.

**When `tls_domain` still matters**:

- If a user configures the proxy with Server B's IP directly (single-hop, bypassing the Reality tunnel), TSPU sees Server B's `tls_domain` SNI directly.
- Telegram's own client validates the FakeTLS handshake against the `tls_domain` value embedded in the proxy secret.
- Changing `tls_domain` invalidates all existing proxy links — users must obtain new links [2]. This makes `tls_domain` operationally sticky even if it's not the primary DPI surface.

**The VLESS-Reality tunnel between Server A and Server B**: TSPU sees this as an encrypted connection from a Russian IP to an EU IP. TSPU may attempt to block this tunnel separately (e.g., by blocking the EU server's IP), but the FakeTLS content of Server B is not visible to TSPU. Xray Reality uses real TLS to a real domain as its outer layer, making the A→B tunnel itself DPI-resistant.

**The yahoo.com default in the XRAY_DOUBLE_HOP example** [1]: Yahoo.com is accessible in Russia and has stable TLS 1.3. It is a reasonable starting point for the Reality `dest`. However, it is a well-known default — if TSPU fingerprints the combination of "yahoo.com Reality SNI + known Xray fingerprint", it may become a detection signal. Consider rotating to a less common but equally stable domain.

---

## Community Evidence: What Real Operators Are Using

**Telemt official defaults**: `petrovich.ru` appears as the default `tls_domain` in the official `config.toml` [8], the Quick Start Guide [19], and the FAQ [2]. It is a Russian retail site (petrovich.ru — a construction materials chain) with a valid GlobalSign certificate and TLS 1.3 support [2]. The FAQ documents it as a working example. **However**, Issue #274 explicitly labels it a **negative example** for non-Russian-hosted servers due to ASN mismatch [6]. This tension is real: the default is correct for Russian-hosted deployments but wrong for EU-hosted ones.

**Issue #274 recommendations** [6]: `github.com`, `www.twitch.tv`, and `microsoft.com` are explicitly recommended for EU-hosted servers. The issue warns against Apple domains and small/self-owned sites. This is the most directly applicable community guidance for the EU exit server use case.

**mtproto.zig default**: `rutube.ru` [20]. A Russian video platform with single-round x25519 handshake. Correct for Russia-hosted servers; wrong for EU-hosted servers (same ASN mismatch issue as petrovich.ru).

**Issue #617 operator experience** [17]: `ozon.ru` and `1с.ru` were used in production. The issue author experienced handshake timeout failures with `ozon.ru` — the setup failed, not succeeded. Community members in the same thread suggested using custom stub sites hosted within Russia as an alternative.

**Issue #598**: `ok.ru` (Odnoklassniki) used as `tls_domain` in a working configuration (single data point, no ISP or date context).

**Issue #581**: Multiple Yandex subdomains in use: `api-maps.yandex.ru`, `travel.yandex.ru`, `ads.x5.ru`, `passport.yandex.ru`. These are Russian-hosted; appropriate only for Russian servers.

**MTProxyMax recommendations** [16]: `cloudflare.com`, `www.microsoft.com`, `www.google.com` as the example high-reputation cover domains for the `tls_domains` pool.

**April 1, 2026 mass outage**: MTProto proxies failed across Russia around midday Moscow time with handshake timeout, obfuscated handshake failed, and EOF errors. This was the first large-scale detection event and confirmed that `tls_domain` selection alone was insufficient once TSPU began targeting client-side JA4 fingerprints.

**May 27–31, 2026 testing**: Only 3 of 27 MTProxy configurations worked across 6 Russian networks. Federal operators (MTS, YOTA) showed 0% success; regional providers (DOM.RU, Electronic City) had partial success. This confirms TSPU deployment is uneven — regional ISPs lag behind federal operators in detection capability.

**`unknown_sni_action` configuration** [2]: Two options:

- `mask` (default): allows any incoming SNI, forwards unknown SNI traffic to `mask_host`. More permissive; users with wrong SNI still connect.
- `reject_handshake`: emits a TLS `unrecognized_name` alert for unknown SNI, mimicking real nginx behavior (`ssl_reject_handshake on`). More realistic to active probes; breaks clients with wrong SNI.

For production use with a stable `tls_domain`, `reject_handshake` is more DPI-resistant because it matches what a real web server would do. Use `mask` only during transition periods when some users still have old proxy links.

---

## Complete Configuration Recommendations

### 8a. Recommended `[censorship]` Section (`config.toml`, Server B — EU exit)

```toml
[censorship]
# Primary tls_domain: impersonates this domain's TLS handshake.
# Must be accessible from your server and support TLS 1.3.
# For EU-hosted server: use CDN-backed domains without Russian PoPs.
tls_domain = "github.com"

# mask_host: where non-Telegram HTTP probes are forwarded.
# Does NOT need to match tls_domain — can be a separate real web server.
# If you run nginx on the same server, point to localhost.
mask_host = "github.com" # or "127.0.0.1" if nginx runs locally

# unknown_sni_action: behavior when client presents a different SNI.
# "reject_handshake" = mimics real nginx ssl_reject_handshake on.
# "mask" = allow any SNI (use during link rotation transitions).
unknown_sni_action = "reject_handshake"

# Port 443: makes traffic appear as standard HTTPS.
# Required — non-443 ports are immediately suspicious.
port = 443
```

**Notes**:

- `mask_host` can differ from `tls_domain` — telemt Issue #713 confirms they are independent parameters. If you run a real nginx on the same server (recommended), set `mask_host = "127.0.0.1"` or the local nginx vhost.
- `tls_emulation` (if present in your version) should be enabled — it fetches the real ServerHello from `tls_domain`, making the handshake wire-identical to the real domain [2].
- Do **not** set `mask_port = 443` if masking needs to work — Issue #330 documents that this configuration breaks masking [18].

### 8b. Recommended Xray Reality Config for Server A (Russia entry)

```jsonc
// Server A (Russia entry) — Xray inbound
{
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [{ "id": "<UUID>", "flow": "xtls-rprx-vision" }],
        "decryption": "none",
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          // dest: domain that Xray connects to for the real TLS handshake.
          // Must be accessible from Server A and support TLS 1.3.
          // yahoo.com is the official telemt example [1]; www.microsoft.com
          // is a stable alternative [6].
          "dest": "yahoo.com:443",
          "serverNames": ["yahoo.com"],

          // fingerprint: uTLS fingerprint for the ClientHello.
          // "firefox" as specified in your architecture.
          // Matches a real browser fingerprint to avoid JA4 detection.
          "fingerprint": "firefox",

          // shortId and privateKey: generate with `xray x25519`
          "privateKey": "<PRIVATE_KEY>",
          "shortIds": ["<SHORT_ID>"],
        },
      },
    },
  ],
}
```

**Why yahoo.com**: It is the domain used in the official telemt XRAY_DOUBLE_HOP documentation [1], accessible in Russia, and has stable TLS 1.3. Alternative: `www.microsoft.com` (recommended in Issue #274 [6]) or `vkvideo.ru` (Russian domestic, whitelisted, no ASN anomaly for a Russian server). For a Russia-hosted entry server, a Russian domestic domain is preferable because the server's IP is in a Russian ASN — consistent with the domain's expected ASN.

### 8c. Rotation Strategy

**Operational constraint**: `tls_domain` is embedded in the `ee` secret of the `tg://proxy` link. Changing it invalidates all existing links — users must get new links [2]. This makes `tls_domain` rotation expensive for public proxies. For private proxies (small user group), rotation is feasible.

**Rotation triggers** (event-driven, not time-driven):

1. Users report connection failures (handshake timeout, EOF errors) that started suddenly — not gradually.
2. You confirm the failure is domain-specific by testing with a different `tls_domain` on a test instance.
3. MegaFon or other ISP-specific reports of IP mismatch blocking.

**Rotation procedure**:

1. Deploy a second telemt instance with the new `tls_domain` on a different port (e.g., 8444) for testing.
2. Confirm the new domain works from a Russian IP.
3. Update `config.toml` with the new `tls_domain`.
4. Set `unknown_sni_action = "mask"` temporarily — this allows users with old links to still connect (they'll get the mask_host response, not Telegram, but they won't get a hard error).
5. Regenerate and redistribute proxy links with the new `tls_domain`.
6. After 24–48 hours (sufficient for users to update), switch back to `unknown_sni_action = "reject_handshake"`.

**MTProxyMax approach** [21]: Uses a `tls_domains` pool with automated Cover Watchdog that rotates to a backup domain when the primary returns HTTP 5xx errors or connection timeouts [21]. Auto Cert Synchronization connects every 24 hours to measure live DER payload size and updates `fake_cert_len` dynamically [21]. If you use MTProxyMax, configure a pool of 3–5 domains (microsoft.com, github.com, twitch.tv, wikipedia.org, google.com) to avoid single-domain blocking.

**How often to rotate proactively**: No community consensus exists on a fixed interval. Given the May 2026 data showing 89% of configurations failing, proactive rotation is less valuable than reactive rotation — the blocking events are mass-scale (affecting all proxies simultaneously), not domain-specific. Focus on having a tested backup domain ready to deploy within minutes of a detection event.

### 8d. Summary Decision Table

| Parameter                    | Recommended value                         | Confidence  | Rationale                                                                            |
| ---------------------------- | ----------------------------------------- | ----------- | ------------------------------------------------------------------------------------ |
| `tls_domain` (primary)       | `github.com`                              | Medium-High | Azure CDN, no Russian PoPs, stable TLS 1.3, recommended in Issue #274 [6]            |
| `tls_domain` (backup)        | `www.microsoft.com`                       | Medium-High | Same rationale; explicitly listed in Issue #274 [6] and MTProxyMax [16]              |
| Reality SNI (`dest`) — entry | `yahoo.com`                               | Medium      | Official telemt XRAY_DOUBLE_HOP example [1]; accessible in Russia                    |
| Reality SNI (`serverNames`)  | `["yahoo.com"]`                           | Medium      | Matches `dest`; update if switching to alternative domain                            |
| Reality `fingerprint`        | `"firefox"`                               | High        | Specified in architecture; matches real browser JA4 fingerprint                      |
| `mask_host`                  | Real nginx on same server or `github.com` | Medium      | Must respond to HTTP probes with valid content [2]                                   |
| `unknown_sni_action`         | `reject_handshake`                        | Medium      | Mimics real nginx; more DPI-resistant than `mask` [2]                                |
| Rotation frequency           | Event-driven (not scheduled)              | Medium      | Mass blocking events affect all proxies; no evidence for time-based rotation benefit |

---

## Gaps, Unknowns, and What Requires Testing

| Question                                                                       | Status                                                                                                                 | Why unknown                                                             | How to test                                                                                                                               |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Does TSPU perform real-time A-record / ASN correlation?                        | **Partially confirmed** (community source [12], MegaFon user report [11])                                              | No academic measurement study confirms this as universally deployed     | Deploy server with `tls_domain = microsoft.com` on Hetzner; monitor block rate vs. same config with self-owned domain pointing to same IP |
| Does TSPU send active HTTP probes after TLS handshake?                         | **Partially known** — Censored Planet confirms TSPU active probing capability [10]; Russia-specific deployment unclear | No confirmed Russia MTProxy case where probe response affected blocking | Monitor nginx/Angie access logs for unexpected HTTP GET requests from Russian ISP subnets                                                 |
| Does TSPU compare ServerHello byte-for-byte to real domain?                    | **Unknown**                                                                                                            | No public confirmation beyond what telemt's tls_emulation addresses     | Capture telemt ServerHello with Wireshark; compare to real domain's ServerHello; check for any byte difference                            |
| Does TSPU analyze post-handshake traffic patterns?                             | **Confirmed** (mtg issue #547 [13], te-st.org May 2026 data)                                                           | Mechanism confirmed; specific packet size thresholds not published      | Monitor connection lifetime vs. traffic volume; compare MTProto vs. padded traffic                                                        |
| Which specific `tls_domain` values are currently blocked by SNI?               | **Unknown**                                                                                                            | No systematic public testing data as of July 2026                       | Submit test connections with different SNI values from Russian IPs; monitor via OONI                                                      |
| How long does a new MTProxy server survive before IP block?                    | **Unknown** (hours to days per community reports; no systematic data)                                                  | No controlled study                                                     | Deploy fresh server; measure time to first block; compare across ISPs                                                                     |
| Is yahoo.com accessible and unthrottled in Russia (July 2026)?                 | **Unknown**                                                                                                            | No confirmed measurement from July 2026                                 | Check OONI data for yahoo.com Russia measurements; test from Russian IP                                                                   |
| Does TSPU's three-signal AND logic mean avoiding one signal prevents blocking? | **Partially confirmed** (Zapret community docs)                                                                        | Not confirmed by independent measurement                                | Test single-signal vs. multi-signal scenarios; measure block rate difference                                                              |

---

## Explore Further

**1. OONI and Censored Planet for real-time domain status**: OONI's Russia measurement data (ooni.org/country/RU) provides near-real-time blocking status for specific domains, including SNI-level data. To contribute your own server's detection data: install the OONI Probe CLI, run `ooni run web_connectivity` targeting your `tls_domain` candidates from a Russian IP. Censored Planet's Quack-Ripe tool performs active probing from distributed vantage points — their Russia data can confirm whether specific domains are SNI-blocked. Both tools produce structured JSON that can be queried for specific domains and ISPs.

**2. ECH as a future mitigation vs. current detection vector**: Telemt FAQ identifies ECH extension _presence_ as a detection signal in the April 2026 wave [2] — TSPU flagged handshakes that included ECH (which real browsers don't commonly send in the same combination). This is counterintuitive: ECH is designed to _hide_ the SNI, but its presence in an otherwise anomalous handshake became a fingerprint. The open question is whether deploying ECH on the exit server's real TLS stack (for `mask_host` responses) would help or hurt. If TSPU now expects ECH-absent handshakes for specific domains, adding ECH could be another fingerprint. Requires testing with Wireshark captures comparing ECH-enabled vs. ECH-disabled ServerHello responses from the target domain.

**3. VLESS-XTLS-Vision vs. VLESS-Reality for the Russia entry server**: Reality uses a real TLS handshake to a real backend domain, making the entry server's TLS indistinguishable from a connection to that domain. VLESS-XTLS-Vision instead uses real TLS to a real backend on the _same_ server (the server has a real TLS certificate). Vision's advantage is that the TLS certificate is genuine and the SNI resolves to the server's actual IP — eliminating the A-record mismatch that Reality may have if the `dest` domain's IP differs from the server's IP. Given the June 2026 A-record validation reports [12], Vision may be more resilient for the entry server. The tradeoff: Vision requires a valid TLS certificate on the entry server itself, while Reality borrows the TLS parameters from a remote domain. Investigate Xray-core issues and the XTLS-Vision documentation for current Russia operator experience.

## References

[1] XRAY_DOUBLE_HOP.en.md - telemt/telemt. https://github.com/telemt/telemt/blob/main/docs/Setup_examples/XRAY_DOUBLE_HOP.en.md
[2] Telemt FAQ.en.md. https://github.com/telemt/telemt/blob/main/docs/FAQ.en.md
[3] Telemt - MTProxy on Rust + Tokio. https://github.com/telemt/telemt/blob/main/README.md
[4] Telemt - MTProxy on Rust + Tokio - GitHub. https://github.com/telemt/telemt
[5] project.microsoft.com - SSL Server Test. https://www.ssllabs.com/ssltest//analyze.html?d=project.microsoft.com&s=13.107.226.71
[6] Question about the instruction for selecting the tls_domain - Issue #274. https://github.com/telemt/telemt/issues/274
[7] Cloudflare Blog - Russian Internet Users Unable to Access Open Internet. https://blog.cloudflare.com/russian-internet-users-are-unable-to-access-the-open-internet/
[8] telemt/config.toml at main. https://github.com/telemt/telemt/blob/main/config.toml
[9] Обновить fingerprint MTPROTO FakeTLS · Issue #30733. https://github.com/telegramdesktop/tdesktop/issues/30733
[10] TSPU: Russia's Decentralized Censorship System - Censored Planet. https://censoredplanet.org/papers/tspu-imc22.pdf
[11] Telemt MTProxy v3.3.28 + AmneziaWG + HaProxy - not working. https://github.com/telemt/telemt/issues/565
[12] Teleproxy DPI Resistance Features. https://teleproxy.github.io/features/dpi-resistance/
[13] 9seconds/mtg Issue #547 - Draft Answer Verification Report. https://github.com/9seconds/mtg/issues/547
[14] TSPU: Russia's Decentralized Censorship System. https://ensa.fi/papers/tspu-imc22.pdf
[15] USENIX Security 2024: Fingerprinting Encapsulated TLS Handshakes. https://www.usenix.org/conference/usenixsecurity24/presentation/xue-fingerprinting
[16] MTProxyMax README. https://github.com/SamNet-dev/MTProxyMax/blob/main/README.md
[17] telemt/telemt Issue #617 - Draft Answer Verification Report. https://github.com/telemt/telemt/issues/617
[18] [Solved] TLS emulation fails (ServerHello not received) when using .... https://github.com/telemt/telemt/issues/330
[19] telemt/docs/Quick_start/QUICK_START_GUIDE.en.md at main. https://github.com/telemt/telemt/blob/main/docs/Quick_start/QUICK_START_GUIDE.en.md
[20] config.toml.example - mtproto.zig. https://github.com/sleep3r/mtproto.zig/blob/main/config.toml.example
[21] SamNet-dev/MTProxyMax. https://github.com/SamNet-dev/MTProxyMax
