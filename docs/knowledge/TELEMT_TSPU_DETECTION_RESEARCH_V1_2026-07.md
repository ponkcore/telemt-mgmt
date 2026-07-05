# TSPU MTProto Detection Research — July 2026

**Date:** 2026-07-05
**Author:** Viktor (TSPU Evasion Researcher)
**Repo:** github.com/ponkcore/telemt-mgmt (ARCH-001@0.2.1)
**Primary source:** `docs/knowledge/TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md` (3rd deploy report, 9 variants)

---

## Executive Summary

**telemt-mgmt cannot work from Russia with standard Telegram clients.** The root cause is not the server-side FakeTLS implementation (which is adequate) — it is the **Telegram client's own TLS ClientHello**, which carries a static JA4 fingerprint that TSPU matches against a signature database. This is a client-side problem the proxy server cannot fix. The 9 deploy variants all failed because the client's fingerprint was visible to TSPU regardless of server-side architecture. The VPN bypass (variant 5) worked because the VPN tunnel hid the client's ClientHello from TSPU entirely.

The project is viable but requires either: (a) client-side JA4 mitigation (tdlib-obf, GoodbyeDPI/zapret/ByeDPI) which conflicts with PRD Non-Goal "no custom client builds", or (b) a transport-layer pivot that removes the Telegram client's TLS stack from the DPI-visible path — the most promising being the tg-ws-proxy WebSocket approach. A third option is to accept that the proxy requires a VPN/tunnel on the client side, which fundamentally changes the product's UX model.

---

## 1. Root Cause: How TSPU Detects MTProto in FakeTLS

### Primary mechanism: Client-side JA4 fingerprinting [confirmed]

**This is the finding that changes everything.** TSPU does not primarily detect MTProto by analyzing the server-side FakeTLS handshake or the encrypted payload. Instead, it matches the **Telegram client's own TLS ClientHello** against a JA4 fingerprint database.

**Evidence:**

- **bugs.telegram.org #62528** (June 2026): "Root cause: Russian DPI now analyzes TLS handshake fingerprints. Official client uses a static JA4 fingerprint in ClientHello. DPI recognises it and injects RST packets. Even Fake TLS is detected because client's TLS stack differs from real browsers." [confirmed — community-verified, multiple independent reports]

- **Proof of client-side causation:** "Community forks with dynamic JA4 rotation (e.g., telemt/tdlib-obf) work immediately with the same proxy and network." [confirmed — bugs.telegram.org #62528, multiple users] — This is the smoking gun. Same proxy, same network, different client = works. The proxy is not the problem.

- **Teleproxy documentation** (teleproxy.github.io): "Detection is **client-side TLS fingerprinting**: the Telegram app's ClientHello carries one fixed JA4 fingerprint that DPI matches against a signature. The proxy cannot change this — the bytes are produced by the Telegram client, not the server." [confirmed]

- **Habr article** (habr.com/ru/articles/1041486/, May 2026): "У реализации Fake-TLS в MTProxy этот отпечаток отличается от настоящего браузера. Не сильно, но измеримо. Где-то другой порядок extensions, где-то отсутствует расширение..." [confirmed — technical analysis of the fingerprint discrepancy]

### Two distinct blocking waves in 2026

**Wave 1 — April 1, 2026** [confirmed]:
- TSPU matched MTProxy FakeTLS ClientHello via specific artifacts: a malformed `0xfe02` extension codepoint and a 20-byte random field that no real browser sends.
- Telegram fixed these client-side (tdesktop PR #30513, DrKLO Android PR #1949).
- This restored connectivity through late May.
- Source: telemt FAQ, teleproxy.github.io, bugs.telegram.org #62528

**Wave 2 — Late May/June 5, 2026** [confirmed]:
- The April fix only swapped one static fingerprint for another — the client still emits a single fixed JA4.
- TSPU now performs **TCP stream reassembly** before fingerprinting. Splitting the ClientHello across segments (MSS clamping to 256 or even 88 bytes) no longer hides the fingerprint on reassembly-capable nodes.
- **Active flow correlation**: Multiple ClientHellos with the same SNI + Telegram's JA4 to the same `ip:port` trigger temporary blocking.
- **A-record cross-check**: The proxy IP is compared against the cover domain's DNS A-record. A mismatch triggers blocking (confirmed on MegaFon).
- Source: teleproxy.github.io, telemt FAQ, bugs.telegram.org #62528

### Hypothesis evaluation

| Hypothesis | Verdict | Evidence |
|---|---|---|
| **H1: Pattern-based DPI (MTProto fingerprinting)** | **Partially confirmed** — but it's the CLIENT's TLS fingerprint, not a payload-level MTProto pattern | JA4 fingerprint match is the primary mechanism. Post-handshake payload analysis is secondary. |
| **H2: TLS interception/mirroring** | **Not confirmed as primary** | No evidence of active TLS interception (cert substitution). TSPU analyzes the ClientHello in cleartext (before encryption), not the encrypted payload. Active probing of suspected proxies is confirmed but separate from detection. |
| **H3: Behavioral analysis** | **Confirmed as secondary** | June 2026 "Siberian" module: 3-signal AND (suspicious subnet + suspicious fingerprint + connection burst). Flow correlation triggers 120s block. But this is additive to JA4 match, not standalone. |
| **H4: MTProto protocol-level detection** | **Confirmed as tertiary** | Post-handshake: "The TLS handshake completes; the moment MTProto Application Data starts, packets are dropped without a reset" (teleproxy.github.io). TSPU detects MTProto by statistical analysis of TLS record sizes, timing patterns, and payload entropy distribution that differ from real HTTPS. (Habr article, FAKETLS_DOMAIN_RESEARCH_2026.md §6) |

### The detection chain (ordered by impact)

1. **JA4 fingerprint match** on ClientHello (instant, high-confidence) → RST injection or silent drop
2. **Flow correlation** (same SNI + JA4 + ip:port, >3 connections in 60s) → 120s block
3. **A-record cross-check** (SNI domain DNS vs actual server IP) → blocking on some ISPs (MegaFon confirmed)
4. **Post-handshake payload analysis** (MTProto Application Data patterns) → silent drop after ~30s
5. **Active probing** (TSPU connects to suspected proxy, sends VPN handshake) → blocklist addition

---

## 2. Evidence Analysis: The 9 Deploy Variants Reinterpreted

The deploy report tested 9 variants and concluded "TSPU blocks MTProto inside FakeTLS." This conclusion is technically correct but misidentifies the mechanism. **Reinterpreting through the client-side JA4 lens:**

| # | Architecture | Why it failed (reinterpreted) | Implication |
|---|---|---|---|
| 1 | Original double-hop (VLESS-Reality + PROXYv1) | Client's JA4 fingerprint visible to TSPU on S1 (client → entry). TSPU sees the static Telegram JA4 in the ClientHello to entry:443 and blocks. | Server architecture is irrelevant if client fingerprint is detectable. |
| 2 | No PROXYv1 | Same as #1. Removing PROXYv1 doesn't change the client's ClientHello. | Confirms PROXYv1 is not the cause. |
| 3 | Self-steal domain + real LE cert | Same as #1. Real cert improves server-side TLS emulation but client JA4 is still static. Self-steal eliminates ASN mismatch but not JA4 match. | Confirms ASN mismatch is not the primary blocking trigger in this deployment. |
| 4 | Disable sniffing | Same as #1. Xray sniffing is irrelevant to client TLS fingerprint. | Confirms Xray config is not the cause. |
| **5** | **Direct telemt :443 via VPN** | **VPN encrypts ALL traffic including the ClientHello.** TSPU sees VPN traffic (which passes because it's VLESS-Reality or similar), not the Telegram JA4 fingerprint. | **Proves the issue is client-side**: same server, same telemt config, just hide the client's TLS stack from TSPU → works. |
| 6 | socat relay (no VLESS) | Same as #1. socat is transparent TCP relay — doesn't modify client's ClientHello. | Rules out Xray-specific issues. |
| 7 | telemt on RU VPS (direct to DCs) | Two issues: (a) client JA4 still visible on S1, AND (b) Telegram DC IPs are blocked outbound from RU servers. | Confirms outbound DC blocking is real. |
| 8 | telemt on RU + tproxy tunnel | Outbound tunnel works (DC connections succeed). But client JA4 still visible on S1 (client → RU VPS). | Proves the outbound path is fixed but inbound path still fails. |
| 9 | telemt on RU + tproxy + self-steal LE cert | Same as #8 with better TLS emulation. Client JA4 still the bottleneck. | Even perfect server-side TLS doesn't help if client fingerprint is detectable. |

### Critical insight from variant 5

Variant 5 is the Rosetta Stone of this analysis. The ONLY difference between variant 5 (works) and variants 8-9 (fail) is whether the CLIENT connects through a VPN:

- **Variant 5**: Client → VPN → HETZNER:443 (telemt). TSPU sees VPN traffic on S1, not Telegram's ClientHello. ✅
- **Variant 9**: Client → VPSVILLE:443 (telemt, self-steal, tproxy). TSPU sees Telegram's ClientHello on S1. ❌

Same telemt, same FakeTLS, same tls_domain. The variable is whether TSPU can see the client's TLS fingerprint. **QED: the server is not the problem.**

### Why the deploy report's conclusion was partially wrong

The report concluded "TSPU blocks MTProto inside FakeTLS." More precisely: **TSPU blocks connections where the ClientHello matches Telegram's known JA4 fingerprint, AND additionally performs post-handshake MTProto pattern analysis as a secondary mechanism.** The FakeTLS is not the weak link — the Telegram client's TLS stack is.

---

## 3. telemt Internals: How FakeTLS Works and What Patterns TSPU Could Match

### FakeTLS (ee-prefix) byte-level operation [confirmed from code analysis]

Based on the GoMTProxy source code documentation (which implements the same protocol as telemt) and telemt's FAQ:

1. **Client sends ClientHello**: The Telegram client constructs a TLS 1.3 ClientHello. The 32-byte `Random` field contains an HMAC proving knowledge of the shared secret, plus a timestamp for replay prevention. The `ee` prefix in the secret means FakeTLS mode. The domain name is encoded in the `ee` secret suffix and placed into the SNI extension.

2. **Server validates**: Proxy computes `HMAC-SHA256(secret, ClientHello_with_zeroed_random)` and XORs with the original Random field. If 28 bytes are zero + valid timestamp → authenticated.

3. **Server sends ServerHello**: Proxy replies with a synthetic ServerHello + ChangeCipherSpec + Application Data. With `tls_emulation = true`, telemt fetches a real ServerHello from the configured `mask_host:mask_port` and replays its extensions, certificate data, and record sizes. This makes the server's TLS response indistinguishable from the real cover domain.

4. **Data transport**: All subsequent data is wrapped in TLS Application Data records (type `0x17`). Inside this framing, the standard obfuscated2 protocol operates (AES-256-CTR encrypted bidirectional relay to Telegram DCs).

### What TSPU matches — it's the CLIENT side

The critical vulnerability is in step 1 — the ClientHello. The Telegram client does NOT use a browser's TLS stack. It uses its own implementation which produces a JA4 fingerprint that differs from any real browser:

- **Specific artifacts (pre-April 2026 fix)**: Malformed `0xfe02` extension codepoint, 20-byte random field [confirmed — teleproxy.github.io]
- **Post-April 2026 fix**: Fixed artifacts but still a static, single JA4 hash per client version. No randomization, no browser profile rotation. [confirmed — bugs.telegram.org #62528]
- **Cipher suite ordering**: Doesn't match Chrome, Firefox, or Safari exactly [confirmed — Habr article]
- **Extensions presence/absence**: Missing or extra extensions compared to real browsers [confirmed — Habr article]

### telemt's server-side defense [confirmed — adequate]

telemt 3.4.22's `tls_emulation` is actually well-designed:

- Fetches real ServerHello from the SNI target domain (72-hour cache TTL)
- Replays extensions from cached profile, includes HMAC authentication
- "TLS mode is completely identical to real-life handshake + communication with a specified host" — telemt FAQ
- "No MITM + No Fake Certificates/Crypto = pure transparent TCP Splice" — telemt FAQ
- Connections without valid secret are forwarded to `mask_host` (real web server) — active probes see legitimate HTTPS

**The server side is not the bottleneck.** telemt's FakeTLS ServerHello is good enough. The problem is the client's ClientHello.

### `tls_emulation` vs fake cert

- `tls_emulation = true`: telemt fetches real ServerHello from `mask_host:mask_port`, emulates TLS record sizes and characteristics. This is the correct configuration.
- `tls_emulation = false`: telemt uses a built-in 2048-byte fake cert. Less realistic but doesn't matter because the client's ClientHello is the detection point, not the ServerHello.
- **Key finding from deploy report**: telemt's rustls TLS fetcher is blocked by CDN WAFs (Akamai, Google, Apple, GitHub). Only self-steal domain (fetching from localhost Angie) works for `tls_emulation`. [confirmed — DEPLOY_EXPERIENCE]

### `use_middle_proxy` and ad_tag

**Does `use_middle_proxy = true` with a real ad_tag change detection?** [speculative — insufficient evidence]

When `use_middle_proxy = true`, telemt connects to Telegram's middle proxy servers (maintained by Telegram) instead of directly to DCs. The MTProto handshake involves additional steps (ad_tag transmission). However:

- The ad_tag affects the **server-to-DC** path, not the **client-to-server** path
- The client's ClientHello (which TSPU sees) is identical regardless of `use_middle_proxy`
- No community reports suggest `use_middle_proxy` affects TSPU detection

**Assessment**: `use_middle_proxy` does NOT affect TSPU detection on S1 (client → entry). It may theoretically affect S3 (exit → DCs) routing but the deploy report tested both settings with identical results from Russia. [confirmed — DEPLOY_EXPERIENCE: "use_middle_proxy: true, false — Both ❌ from RU"]

### Alternative telemt modes

- **Obfuscated2 (`dd` prefix)**: Random padding applied to MTProto packets. Helps against size-based heuristics on some ISPs but does nothing against JA4 detection. [confirmed — teleproxy.github.io: "helps against size-based heuristics on some ISPs, but does nothing against the JA4 detection driving the June 2026 wave"]
- **No other transport mode**: telemt does not support WebSocket, HTTP/2, or any transport other than FakeTLS and raw obfuscated2 for the client-facing side. [confirmed — code structure, FAQ]

---

## 4. Community Findings

### Working configurations (July 2026)

| Solution | Works? | Mechanism | Source |
|---|---|---|---|
| **tg-ws-proxy (Flowseal)** | ✅ Working | Routes MTProto through WebSocket (TLS) to `kws*.web.telegram.org` — TSPU sees only HTTPS to whitelisted Telegram domains | GitHub Flowseal/tg-ws-proxy, Habr article |
| **tdlib-obf (telemt fork)** | ✅ Working | JA4 randomization in client ClientHello — TSPU sees browser-like fingerprint | bugs.telegram.org #62528, GitHub telemt/tdlib-obf |
| **GoodbyeDPI / zapret / ByeDPI** | ✅ Partially working | Client-side DPI evasion (packet fragmentation, RST countermeasure) — works on non-reassembling TSPU nodes only | bugs.telegram.org #62528, multiple community reports |
| **MTProxy + VLESS-Reality VPN** | ✅ Working | VPN hides client's ClientHello from TSPU | Deploy report variant 5 |
| **mtg 2.2.8** | ✅ Server-side improved | Server-side JA4S parity with Chrome 132, dynamic GREASE, browser-aligned cipher suites | YouTube analysis, mtg #449 |
| **Free MTProxy lists** | ⚠️ Unstable | Public proxies die within 48 hours on federal ISPs. Work on regional ISPs. | te-st.org research (May 2026): only 3/27 configs worked |
| **Standard Telegram client + any proxy** | ❌ Blocked | Client's static JA4 fingerprint detected | bugs.telegram.org #62528, all ISPs confirmed |

### ISP-level variation (May 2026 field test)

te-st.org conducted a controlled study across 4 regions and 6 ISPs, testing 27 MTProxy configurations:

| Region | ISP | Type | Tested | Working |
|---|---|---|---|---|
| Ростов-на-Дону | ДОМ.РУ | Home | 11 | 1 |
| Ростов-на-Дону | МегаФон | Mobile | 11 | 1 |
| Московская обл. | МТС | Mobile 4G | 4 | **0** |
| Московская обл. | Инфолинк | Home | 4 | **0** |
| Екатеринбург | YOTA | Mobile 4G | 4 | **0** |
| Новосибирск | Электронный город | Home | 4 | 2 |

**Key finding**: Working proxies were only on regional ISPs. Federal operators (МТС, YOTA) showed **0% success rate**. The same proxy worked on one ISP but not another in different regions — confirming TSPU deployment is uneven across ISPs. [confirmed — te-st.org, May 2026]

### tg-ws-proxy: Why it works [confirmed — Habr, GitHub]

This is the most significant community finding for the project:

1. Runs a local SOCKS5/MTProto proxy on `127.0.0.1:1443`
2. Telegram Desktop connects to the local proxy
3. Proxy intercepts MTProto obfuscation init packet, extracts DC ID
4. Establishes WebSocket (TLS) connection to `kws{N}.web.telegram.org` (Telegram's own WebSocket endpoint, same as web.telegram.org uses)
5. MTProto data is wrapped inside WebSocket inside TLS
6. TSPU sees only HTTPS to `*.web.telegram.org` — a **whitelisted domain**

**Why TSPU doesn't block it**: The Telegram web client uses the exact same WebSocket endpoints. Blocking `kws*.web.telegram.org` would break web.telegram.org for all Russian users. TSPU doesn't want to block the web version (at least not yet). The TLS ClientHello to these domains comes from the local proxy's TLS stack (Python/Go), NOT from the Telegram client's custom TLS stack — so the JA4 fingerprint is different.

**Limitations**: Desktop only (Windows, Linux, macOS). Not available for Android/iOS. Requires installing a local application. Single point of failure if Telegram changes their WebSocket API. No ad_tag support (no channel promotion).

### Teleproxy: Another MTProxy implementation [confirmed — teleproxy.github.io]

Teleproxy has documented DPI resistance features:
- Chrome-profile ClientHello on the server side (JA3S parity with Chrome 132)
- Graduated TLS record sizes matching real web servers
- ServerHello size variation (±32 bytes across connections)
- ServerHello and ChangeCipherSpec sent as separate TCP segments
- Random padding on records to defeat uniform-size fingerprinting

**However**: Teleproxy's documentation explicitly acknowledges that these server-side measures are insufficient against the June 2026 wave: "Detection is **client-side TLS fingerprinting**: the Telegram app's ClientHello carries one fixed JA4 fingerprint that DPI matches against a signature. The proxy cannot change this."

### Academic sources

- **Censored Planet TSPU-IMC22 paper** [confirmed]: Documents TSPU hardware (RDP.RU), decentralized deployment within ~2 hops of end users, SNI inspection, packet modification capabilities.
- **OONI 2024 Russia report** [confirmed]: TLS interference is the dominant blocking method. RST injection after ClientHello. Centrally managed blocks via TSPU on 400+ ASes.
- **No July 2026 academic papers found** on MTProto-specific detection. The most current technical analysis is from community sources (Habr, teleproxy.github.io).

---

## 5. Alternative Approaches Evaluated

### A1: Different transport for MTProto (WebSocket / HTTP/2)

**Feasibility**: ⭐⭐⭐⭐ (high for client-side; impossible server-side without protocol changes)

**tg-ws-proxy approach**: Already working. Routes MTProto through Telegram's own WebSocket endpoints (`kws*.web.telegram.org`). TSPU sees only HTTPS to whitelisted domains.

- **Pros**: No server infrastructure needed. Works today. Free. Uses Telegram's own infrastructure.
- **Cons**: Desktop only. Requires local app installation. No ad_tag (channel promotion). No `tg://proxy` link distribution — fundamentally different UX.
- **PRD compatibility**: ⚠️ **Violates G1** (user obtains link via bot button — tg-ws-proxy doesn't work via `tg://proxy` links). Violates G6 (embeddable package). Violates G7 (ad_tag promotion).

**Server-side WebSocket wrapping**: Theoretically, a modified MTProxy server could accept WebSocket connections and wrap MTProto inside them. This would require:
1. A custom client that connects via WebSocket instead of raw TCP
2. The server unwraps WebSocket, processes MTProto normally
3. This is essentially what tg-ws-proxy does, but with a custom server instead of Telegram's servers

- **Effort**: High (custom client + custom server transport)
- **PRD impact**: Would require custom client — violates Non-Goal "no custom client builds"

**XHTTP transport**: Xray's XHTTP wraps traffic in HTTP/2 over TLS. Could potentially wrap MTProto, but:
- Requires Xray on both client and server side
- Users need Xray/v2ray client app — no standard `tg://proxy` link
- This is essentially approach A2 (different proxy protocol)

### A2: Different proxy protocol entirely (VLESS/VMess/Trojan)

**Feasibility**: ⭐⭐⭐⭐ (proven working in Russia)

Replace MTProxy with VLESS-Reality as the client-facing protocol. Users install v2rayNG / Hiddify / NekoBox / Streisand on their devices and connect through VLESS-Reality, which then tunnels all Telegram traffic.

- **Pros**: VLESS-Reality with Vision is the currently most reliable protocol for bypassing TSPU. Production-proven, actively maintained, supported by multiple client apps.
- **Cons**: No `tg://proxy` links. Users must install a VPN app. Cannot promote operator's channel via ad_tag. Completely different product — essentially a VPN, not a Telegram proxy.
- **UX impact**: Dramatic. Instead of "tap link → connected", it's "install app → import config → enable VPN → open Telegram". Much higher friction.
- **PRD compatibility**: ❌ **Violates G1** (no bot button flow), **G6** (not embeddable), **G7** (no ad_tag). Effectively a different product.
- **Config distribution**: Telegram bot CAN distribute VLESS configs (as text or deep links for v2rayNG). This is how most Russian VPN operators distribute configs today.

### A3: WireGuard / AmneziaWG tunnel

**Feasibility**: ⭐ (WireGuard) / ⭐⭐ (AmneziaWG)

**WireGuard**: "Actively blocked, near-100% accuracy on initiation packet (since 2023)" [confirmed — fexyn.com, multiple sources]. **Not viable.**

**AmneziaWG**: Uses UDP with obfuscation. "Overall, it operates stably, though the regulator periodically blocks its signatures, necessitating regular updates" [confirmed — TechRadar, Amnezia blog]. Russia throttled unidentified UDP traffic since summer 2025. In June 2026, Amnezia's infrastructure suffered a combined DDoS + IP blocking attack from Roskomnadzor. [confirmed — Amnezia blog June 2026]

**WireGuard over TCP**: Possible via `udp2raw` or `wstunnel`, but adds latency and complexity. No community reports of WireGuard-over-TCP working reliably from Russia in 2026.

- **Pros**: If working, provides full VPN tunnel hiding all traffic from TSPU.
- **Cons**: WireGuard blocked outright. AmneziaWG requires frequent signature updates and is unstable. UDP throttling is systemic.
- **PRD compatibility**: ❌ Violates Non-Goals (requires custom client app). Same UX issues as A2.

### A4: Xray tproxy on client side

**Feasibility**: ⭐⭐⭐ (technically sound, UX-problematic)

User installs Xray/v2rayNG on their device. Local Xray wraps ALL outbound traffic (or just Telegram traffic) in VLESS-Reality before sending to the entry server. TSPU sees VLESS-Reality (looks like HTTPS to a CDN domain), not the Telegram client's JA4 fingerprint.

- **Pros**: Proven working (this is essentially what variant 5's VPN does). Hides client fingerprint completely. Compatible with existing server architecture.
- **Cons**: Requires user to install and configure a VPN/proxy app. Not distributable via `tg://proxy` link. Significant UX friction.
- **PRD compatibility**: ❌ Violates Non-Goal "no custom client builds" and dramatically changes G1 UX.
- **Distribution**: A Telegram bot COULD distribute VLESS configs and QR codes. v2rayNG supports QR code scanning. This is the most plausible distribution model.

### A5: telemt with real ad_tag and use_middle_proxy

**Feasibility**: ⭐ (does not address root cause)

**Assessment**: The deploy report already tested `use_middle_proxy = true` and `use_middle_proxy = false`. Both failed from Russia. [confirmed — DEPLOY_EXPERIENCE: "use_middle_proxy: true, false — Both ❌ from RU"]

`use_middle_proxy` changes the server-to-DC routing (telemt connects to Telegram's middle proxy servers instead of DCs directly). It does NOT change:
- The client's TLS ClientHello (which TSPU fingerprints)
- The client's JA4 hash
- The FakeTLS handshake on S1

**Recommendation**: **Reject** — does not address the root cause. No evidence it affects TSPU detection in any way.

### A6: EU VPS provider not blocked from Russia

**Feasibility**: ⭐⭐ (does not address root cause but could enable fallback)

The deploy report notes Hetzner (AS24940) is blocked from Russia for direct telemt connections. Other EU providers might not be blocked:

- **NodeHost (Sweden)**: Used as mgmt server in deploy. Needs direct telemt testing from Russia.
- **Contabo (Germany)**: Different ASN from Hetzner. Might not be blocked.
- **OVH (France)**: Large provider, different IP ranges.
- **Oracle Cloud**: Free tier available, different ASN.
- **Scaleway**: French provider, different ASN.

**However**: Even if an unblocked EU IP is found, the client's JA4 fingerprint is still the primary detection mechanism. Direct telemt on an unblocked IP would only help if:
1. That specific IP range hasn't been flagged by TSPU behavioral analysis
2. The client's JA4 fingerprint somehow passes on that ISP's TSPU node (ISP-specific variation)
3. The deploy report's variant 5 VPN bypass suggests IP blocking is NOT the primary mechanism

**Assessment**: Finding an unblocked EU IP might allow telemt to work on *some* regional ISPs where TSPU JA4 detection is not yet deployed, but will not work on federal ISPs (МТС, YOTA, МегаФон, Ростелеком) where JA4 fingerprinting is confirmed active. This is a temporary measure at best.

### A7: Multi-stage TLS wrapping (double TLS)

**Feasibility**: ⭐⭐ (theoretically sound, practically complex)

Wrap MTProto in FakeTLS, then wrap the entire connection in another real TLS layer (e.g., stunnel or Xray TLS). TSPU would see the outer TLS layer (with a real browser-like fingerprint), not the inner FakeTLS.

**However**: This is essentially what VLESS-Reality does for S2 (entry → exit). For S1 (client → entry), this would require the CLIENT to perform the outer TLS wrapping — which means a client-side app (back to A4).

If done server-side only (e.g., entry server terminates outer TLS, then passes to telemt), the client's original ClientHello is still visible to TSPU on the first hop. Double-TLS doesn't help unless the CLIENT'S outbound TLS is browser-like.

**Assessment**: **Equivalent to A4** (Xray tproxy on client side). The concept is sound but requires client-side software. No advantage over A2/A4.

### Summary: Alternative viability matrix

| Approach | Technical viability | UX impact | PRD compatibility | Effort | Recommendation |
|---|---|---|---|---|---|
| **A1: tg-ws-proxy model** | ⭐⭐⭐⭐⭐ | High friction (app install) | ⚠️ Breaks G1, G6, G7 | Medium | **Investigate — most promising** |
| **A2: VLESS-Reality VPN** | ⭐⭐⭐⭐⭐ | Very high friction | ❌ Different product | High | **Viable pivot if PRD revised** |
| **A3: WireGuard/AmneziaWG** | ⭐ / ⭐⭐ | Very high friction | ❌ | Medium | **Reject** (blocked) |
| **A4: Client-side Xray** | ⭐⭐⭐⭐ | High friction | ❌ Non-Goal | Medium | **Subset of A2** |
| **A5: ad_tag/middle_proxy** | ⭐ | None | ✅ | Zero | **Reject** (doesn't help) |
| **A6: Non-blocked EU IP** | ⭐⭐ | None | ✅ | Low | **Test but don't rely on it** |
| **A7: Double TLS** | ⭐⭐ | Same as A4 | ❌ | High | **Reject** (= A4 with more complexity) |

---

## 6. Recommendations

### Priority 1: Establish ground truth [immediate]

**Test the client-side hypothesis directly.** The deploy report tested server-side variations but never tested client-side variations. Before any architecture changes:

1. **Test with tdlib-obf client** against the existing telemt deployment (VPSVILLE or HETZNER). If tdlib-obf + telemt works from Russia without VPN, this confirms the root cause is 100% client-side and telemt's server-side FakeTLS is adequate.

2. **Test with GoodbyeDPI/zapret/ByeDPI** on the client side with the same proxy. If these work on some ISPs, it narrows the issue to specific TSPU detection mechanisms.

3. **Test with tg-ws-proxy** to confirm it works from the test location. This validates the WebSocket bypass path.

### Priority 2: Client-side JA4 mitigation strategy [short-term]

If tdlib-obf confirms the hypothesis, the project has two paths:

**Path A — Accept client-side requirement:**
- Revise PRD Non-Goal to allow tdlib-obf builds
- Distribute tdlib-obf APKs/builds via the Telegram bot
- telemt-mgmt server infrastructure works as-is (ARCH-001@0.2.1 is adequate)
- GoodbyeDPI/zapret/ByeDPI as lightweight alternatives for users who won't install a custom client

⚠️ **PRD Non-Goal conflict**: "Building or distributing custom Telegram clients (tdlib-obf)" is explicitly listed as a Non-Goal. The PO must decide whether to revise this.

**Path B — Adopt tg-ws-proxy model as a parallel distribution channel:**
- Keep telemt-mgmt for `tg://proxy` link distribution (works for users with VPN or tdlib-obf or DPI tools)
- Add a tg-ws-proxy download link to the bot for users where `tg://proxy` doesn't work
- This is a compromise: some users get zero-friction proxy, others need to install an app

### Priority 3: Architecture decision [medium-term]

If testing confirms that telemt + standard Telegram client cannot work from Russia on any ISP without client-side tools:

**The PO needs to answer a fundamental question:**

> Is telemt-mgmt a **Telegram proxy** (zero-friction, `tg://proxy` link, ad_tag promotion) or a **Telegram access tool** (requires client-side software, prioritizes reliability over UX)?

- If **proxy**: The project is blocked until Telegram fixes their client's JA4 fingerprint (bug #62528 is "Fixed" but community reports say standard clients are still blocked as of July 2026). Mitigation: wait for Telegram to ship the fix, plus offer tdlib-obf as interim.

- If **access tool**: Pivot to VLESS-Reality distribution via bot (A2), which is proven working and widely used in Russia. Lose ad_tag, lose `tg://proxy` links, but gain reliability. This is a fundamentally different product.

- If **both**: Hybrid model. `tg://proxy` links for users with updated clients / regional ISPs where MTProxy works. VLESS-Reality configs for users on federal ISPs where JA4 blocking is active. Bot distributes both options based on user's reported ISP.

### Priority 4: Things to NOT do

1. **Do not invest more time in server-side FakeTLS optimization.** The server side is not the bottleneck. telemt's FakeTLS is adequate. Self-steal domain, encrypted S2, Russian SNI — all good practices, but none address the client-side JA4 issue.

2. **Do not pursue WireGuard or AmneziaWG.** WireGuard is blocked. AmneziaWG is unstable and resource-intensive to maintain.

3. **Do not pursue `use_middle_proxy` as a fix.** Already tested, doesn't help.

4. **Do not rotate tls_domain expecting it to fix the blocking.** The blocking is JA4-based, not SNI-based (for the primary mechanism). Domain rotation is good hygiene but won't unblock federal ISPs.

### Priority 5: Monitoring and adaptation [ongoing]

- Monitor Telegram client updates for official JA4 fix. Bug #62528 is marked "Fixed" — test each new client version from Russia.
- Monitor `free.glushilok.net` and similar public MTProxy lists — if they start working on federal ISPs, it means TSPU has changed its detection rules.
- Monitor tg-ws-proxy for stability and Telegram's potential blocking of `kws*.web.telegram.org` from Russia.

---

## 7. Impact on telemt-mgmt Architecture

### Does ARCH-001 need a major revision?

**No — with caveats.** ARCH-001@0.2.1's server-side architecture is sound:
- Encrypted S2 via VLESS-Reality (ADR-009) ✅ — correct defense against post-handshake payload analysis
- PROXYv1 instead of PROXYv2 ✅ — correct defense against binary signature detection
- Russian domestic Reality SNI ✅ — correct defense against ASN mismatch
- Self-steal domain for tls_emulation ✅ — correct defense against A-record cross-check

The architecture is well-designed for the server side. The problem is entirely client-side and outside the scope of the current architecture.

### What needs to change

1. **PRD-001 §0 Decision Brief needs a new assumption**: "Standard Telegram clients may not work from Russia due to client-side JA4 fingerprint detection by TSPU. The project must accommodate client-side mitigation (tdlib-obf, DPI tools, VPN) as a required deployment step, not just a fallback."

2. **PRD-001 §3 Non-Goals**: The PO should reconsider "tdlib-obf custom client builds" as a Non-Goal, given that it is currently the most effective and least-friction fix for the root cause.

3. **PRD-001 §7 Constraints**: Add "Standard Telegram clients are blocked on federal Russian ISPs (МТС, YOTA, МегаФон, Ростелеком) as of July 2026. Client-side JA4 mitigation is required for these ISPs."

4. **ARCH-001 §1 Overview**: Add a C8 component or extend C2 (bot) to distribute client-side mitigation tools (tdlib-obf builds, tg-ws-proxy downloads, GoodbyeDPI/zapret/ByeDPI instructions).

5. **No ADRs affected by this finding.** ADR-009 (encrypted S2) is correct and should be kept. The server-side architecture decisions are all valid.

### Is the project viable?

**Yes, with revised expectations.** The project is viable if:

1. Telegram ships an official JA4 fix (possible — bug #62528 is "Fixed") — in which case telemt-mgmt works exactly as designed with zero changes.

2. The PO accepts that users on federal ISPs need client-side tools (tdlib-obf, GoodbyeDPI, ByeDPI) — the bot can distribute these alongside `tg://proxy` links.

3. The PO accepts a hybrid model where some users get `tg://proxy` links (working on regional ISPs or with updated clients) and others get VLESS configs or tg-ws-proxy.

**The project is NOT viable if** the PO insists on zero-friction `tg://proxy` links working for all users on all Russian ISPs with standard Telegram clients. This is not achievable given TSPU's July 2026 capabilities.

---

## Appendix A: Key Sources and Confidence Levels

| Source | Type | Confidence | Key finding |
|---|---|---|---|
| bugs.telegram.org #62528 | Bug report + community discussion | High | Client-side JA4 is the root cause; tdlib-obf works |
| teleproxy.github.io/features/dpi-resistance | Technical documentation | High | Two 2026 blocking waves; client-side fingerprinting confirmed |
| habr.com/ru/articles/1041486/ | Technical analysis (Russian) | High | Three detection levels: handshake → behavioral → statistical |
| te-st.org/2026/06/02/mtproxyout/ | Field research (27 configs, 6 ISPs) | High | 3/27 working; federal ISPs 0% success |
| TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md | First-party deploy report | High | 9 variants tested; only VPN works |
| TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md | Research document in repo | High | Path-dependent strategy; detection vectors |
| Amnezia blog (June 2026) | Project blog | Medium | AmneziaWG infrastructure attacked, UDP throttled |
| fexyn.com/vpn-for-russia | Commercial VPN analysis | Medium | WireGuard blocked; VLESS-Reality working |
| GitHub Flowseal/tg-ws-proxy | Open source project | High | WebSocket bypass via Telegram's own endpoints |
| Censored Planet TSPU-IMC22 paper | Academic paper | High | TSPU infrastructure, DPI capabilities |

## Appendix B: Glossary

| Term | Definition |
|---|---|
| **TSPU** | Технические средства противодействия угрозам — DPI devices installed at Russian ISPs, centrally managed by Roskomnadzor |
| **JA4** | TLS ClientHello fingerprint format (successor to JA3) — hash of cipher suites, extensions, ALPN |
| **FakeTLS** | MTProxy mode (`ee` prefix) that wraps MTProto inside TLS-like framing |
| **S1** | Segment 1: Client → Entry server (RU) |
| **S2** | Segment 2: Entry server (RU) → Exit server (EU) |
| **S3** | Segment 3: Exit server (EU) → Telegram DCs |
| **tdlib-obf** | telemt's fork of TDLib with JA4 randomization and DPI resistance |
| **tg-ws-proxy** | Local proxy that routes Telegram Desktop through WebSocket to `kws*.web.telegram.org` |
| **Reality** | Xray TLS variant that fetches real ServerHello from a cover domain |
