# TSPU MTProto Detection Research — July 2026

## Executive Summary

**telemt-mgmt cannot work from Russia without VPN under its current architecture (ARCH-001@0.2.1).** All 9 tested architecture variants fail from Russia; the root cause is a two-layer TSPU detection mechanism: (1) JA4/JA4+ fingerprinting of the Telegram client's static TLS ClientHello, deployed nationwide on June 5, 2026, and (2) post-handshake payload analysis of the MTProto Application Data stream with full TCP stream reassembly, active since at least April 2026 [1][2][3]. Server-side changes — cert quality, SNI matching, relay topology, PROXYv1/v2 configuration — cannot address either layer because both detection signals originate on the **client side** of the connection. The single most important thing that needs to change is a PRD decision: the telemt developers themselves now recommend `tdlib-obf` for client-side fingerprint evasion [4], which is explicitly prohibited by PRD-001's Non-Goals [5]. Until the PO resolves that conflict, the solution space within PRD constraints is limited to low-probability workarounds.

---

## 1. Root Cause: How TSPU Detects MTProto in FakeTLS

### H1: Pattern-based DPI — **Confirmed (primary mechanism)**

TSPU analyzes the TCP stream payload after the TLS handshake completes. The intervention point is the start of Application Data transmission, not the handshake itself: TCP SYN, ClientHello, and ServerHello exchanges complete normally, then TSPU drops packets silently (no TCP RST) when the first MTProto Application Data record arrives, causing the ~30-second handshake timeout seen in all 9 variants [2].

TSPU performs full TCP stream reassembly before classification [2]. This defeats fragmentation-based evasion: splitting the ClientHello across TCP segments or clamping MSS to 88 bytes (as `mtproto.zig` implements) does not prevent TSPU from reconstructing and analyzing the full stream [6].

The specific payload patterns TSPU can match inside the FakeTLS stream include:

- The initial 64-byte MTProto auth key ID block that appears in the first Application Data record after the fake handshake
- The deterministic record size sequence that telemt's `FakeTlsWriter` emits: Phase 1 records at 1,369-byte payload (wire size 1,374 bytes = 1,369 + 5-byte header), Phase 2 at 4,096 bytes, Phase 3 at 16,384 bytes [6]
- The absence of a content-type byte and AEAD tag that real TLS 1.3 includes — telemt's `FakeTlsWriter` adds only the 5-byte TLS record header [6]
- The ServerHello's fixed 32-byte zero `random` field (`[0]`) instead of cryptographically random bytes [7]
- The deterministic record sequence: ServerHello → ChangeCipherSpec → ApplicationData → optional NewSessionTicket-as-ApplicationData [7]

Additionally, TSPU on MegaFon/MTS mobile networks specifically inspects the ServerHello packet size (~200–202 bytes) and drops connections where the ServerHello fits within a single TCP segment [8].

**JA4/JA4+ fingerprinting** is a separate but related detection layer. JA4 is a TLS fingerprinting method that hashes the ClientHello's TLS version, cipher suites, extensions, and ALPN values into a short identifier — analogous to JA3 but more structured and harder to spoof accidentally. TSPU deployed a nationwide JA4/JA4+ blocking wave on June 5, 2026, targeting the static fingerprint emitted by official Telegram clients (`t13d1516h2_8daaf6152771_d8a2da3f94cd`, mimicking Chrome 134 on macOS) [3][4]. This is distinct from payload-level DPI: JA4 operates during the TLS handshake on the ClientHello, before any Application Data is exchanged. It means TSPU can block the connection even before the MTProto payload is transmitted. The April 1, 2026 wave targeted ECH extension presence and cipher suite ordering anomalies; the June 5 wave added JA4/JA4+ hash matching [3].

[confirmed] H1 is the primary detection mechanism. Both sub-layers (post-handshake payload analysis and ClientHello JA4 fingerprinting) are independently confirmed.

### H2: TLS Interception / Active Probing — **Partially supported, not the primary mechanism**

Variant 9 is the decisive test for H2: a self-steal domain with a valid Let's Encrypt certificate, correct SNI, and correct ASN match was deployed — eliminating every variable that active TLS interception would care about — and TSPU still blocked [1]. If TSPU were performing cert substitution or active probing that depends on cert validity, variant 9 would have succeeded. It did not.

TSPU more likely performs **passive mirroring** to a DPI analysis backend rather than active interception. The blocking manifests as silent packet drops (not TCP RST), consistent with a passive inline device that discards matching traffic without injecting reset packets [2].

`tls_emulation = true` vs `false` is practically irrelevant in 2026: telemt's rustls TLS fetcher is blocked by CDN WAFs, causing `tls_emulation` to always fall back to the built-in fake cert [1]. The practical difference between the two modes has collapsed to zero. Even when the cache is populated, the ClientHello fingerprint issue is on the Telegram client side, not the proxy server side — and the fake cert's ServerHello has the structural anomalies described under H1 regardless.

[confirmed] H2 is not the primary mechanism. Variant 9 rules out cert/SNI-based interception as the blocking trigger.

### H3: Behavioral / IP-based Analysis — **Supported as a contributing layer, not standalone**

Hetzner AS24940 is confirmed blocked from Russia [1]. TSPU maintains a database of suspicious CIDR/ASN ranges including Hetzner, DigitalOcean, and OVH, flagged since late May/early June 2026 [3]. This is a contributing signal, not the sole mechanism: the ASN check is one input into a multi-signal decision, not a binary block. Evidence from the knowledge base describes TSPU using three-signal AND logic combining suspicious ASN, non-browser TLS fingerprint, and connection frequency [3].

TSPU performs DNS A-record lookups on the SNI/`tls_domain` and compares the resolved IP against the actual server IP. MegaFon specifically enforces this ASN cross-check [9]. This explains why using a `tls_domain` that resolves to a different ASN than the exit server triggers additional suspicion.

Rotating the entry server IP would help briefly — until the new IP is flagged. The correlation marker TSPU uses (multiple clients connecting to the same server with an identical JA4 fingerprint) means that any server receiving Telegram client traffic will accumulate the same fingerprint pattern and be flagged regardless of IP address.

[confirmed] H3 contributes to detection but cannot explain the variant 9 failure alone. IP rotation is a temporary measure at best.

### H4: MTProto Protocol-Level Detection Inside FakeTLS — **Supported, subsumed by H1**

The `ee` prefix in the proxy secret signals FakeTLS mode to the Telegram client. At the byte level, `ee` itself is not transmitted over the wire — it is a local configuration signal. What matters is the Application Data structure after the fake handshake: the first MTProto Application Data record contains the 64-byte auth key ID followed by the encrypted MTProto handshake, which has a specific statistical structure (high entropy, specific length distribution) that TSPU's payload classifier targets [2][6].

The `dd` prefix (secure/random padding mode) adds random padding to MTProto packets before the FakeTLS wrapper, making the payload size distribution less predictable [10]. This was effective against earlier DPI systems but does not address the JA4 ClientHello fingerprinting layer or the full TCP stream reassembly that TSPU now performs.

`use_middle_proxy = true` with a real `ad_tag` does not change the MTProto handshake structure for TSPU detection purposes [1]. The ad_tag affects Telegram's internal routing for the official proxy program; it does not modify the TLS ClientHello or the Application Data pattern that TSPU inspects.

[confirmed] H4 is real but is subsumed by H1: the payload patterns H4 describes are what H1's post-handshake analysis targets.

### Synthesis

The relay-breaks-handshake pattern (variants 1–4 and 6 all fail; variant 5 via VPN works) is diagnostic in a specific way. Variant 6 used socat — a transparent TCP relay with zero protocol modification. If socat breaks the handshake, the relay itself is not adding a detectable signature. The more likely explanation is that the socat relay introduces a different source IP, which may sit in a flagged ASN, or that the routing path through the relay causes the connection to traverse a different TSPU inspection point with stricter rules. The underlying MTProto payload detection operates independently of whether a relay is in the path.

The combined picture: TSPU blocks at two independent stages. Stage 1 (ClientHello): JA4/JA4+ hash of the Telegram client's static TLS fingerprint is matched and the connection is dropped before Application Data. Stage 2 (Application Data): for connections that pass Stage 1 (e.g., a patched client), TSPU performs full TCP stream reassembly and payload analysis to detect MTProto patterns inside the FakeTLS stream. Both stages must be defeated simultaneously, and both require client-side changes.

---

## 2. Evidence Analysis: What Each Variant Tells Us

| #   | Architecture                         | Result               | What It Proves / Rules Out                                                                                              |
| --- | ------------------------------------ | -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1   | Double-hop (VLESS-Reality + PROXYv1) | ❌ Handshake timeout | Baseline failure; VLESS entry does not hide MTProto client fingerprint                                                  |
| 2   | No PROXYv1                           | ❌ Handshake timeout | Rules out PROXYv1 header as the detection trigger                                                                       |
| 3   | Self-steal domain + real LE cert     | ❌ Handshake timeout | Rules out SNI/ASN mismatch as primary cause; detection is deeper                                                        |
| 4   | Disable sniffing                     | ❌ Handshake timeout | Rules out Xray sniffing as the cause                                                                                    |
| 5   | Direct telemt:443 via VPN            | ✅ Works             | Control: TSPU bypassed entirely; confirms issue is inbound Russian ISP path                                             |
| 6   | socat relay (no VLESS)               | ❌ Handshake timeout | socat is protocol-transparent; failure points to IP/ASN or payload detection, not relay-protocol signatures             |
| 7   | telemt on RU VPS (direct to DCs)     | ❌ DCs blocked       | Separate blocking layer: Telegram DC IP ranges blocked from Russian IP space outbound                                   |
| 8   | RU VPS + Xray tproxy outbound to EU  | ❌ Handshake timeout | Outbound tunnel works (0–1ms DC connections); client-side handshake still blocked                                       |
| 9   | RU VPS + tproxy + self-steal LE cert | ❌ Handshake timeout | Most diagnostic: valid LE cert + correct SNI + correct ASN — TSPU still blocks. Rules out cert/SNI/ASN as the mechanism |

**Variants 1–4 and 6** [confirmed]: Any relay in the client path fails. Variant 6 (socat) is particularly telling — socat does not modify the TCP stream, so the relay itself is not adding a detectable signature. The most likely explanation is that the relay's IP sits in a flagged ASN, or that the connection path traverses a TSPU node with the JA4 ban active. The underlying payload detection is independent of relay presence.

**Variant 5** [confirmed]: The control case. VPN tunnels the entire connection past TSPU's inspection point. This confirms the problem is the Russian ISP inspection path, not the exit server configuration or Telegram DC connectivity.

**Variant 6** [confirmed]: socat is a dumb TCP forwarder. Its failure means TSPU is not just detecting relay-specific protocol signatures — it is detecting the Telegram client's JA4 fingerprint or the MTProto payload regardless of the relay intermediary. This rules out the hypothesis that "if we just hide the VLESS layer, FakeTLS will work."

**Variant 7** [confirmed]: A separate, independent blocking layer. Telegram DC CIDR ranges are blocked from Russian IP space at the network/IP layer. This means a Russia-based exit server cannot reach Telegram DCs directly, regardless of what transport is used. This is why variants 8–9 route outbound traffic through a tproxy tunnel to an EU server.

**Variants 8–9** [confirmed]: The outbound tproxy tunnel to EU achieves 0–1ms DC connections, proving the exit server → Telegram DC path is functional. The client → entry server handshake is still blocked. This isolates the failure to the inbound segment exclusively — the entry server's IP, the client's TLS fingerprint, and the MTProto payload are all visible to TSPU before any tunnel is established.

**Variant 9** [confirmed, most diagnostic]: Valid Let's Encrypt certificate, correct SNI, correct ASN — TSPU still blocks. This is the hardest evidence against H2 (TLS interception) and H3 (ASN-only blocking). The blocking mechanism operates at a layer that cert quality and SNI matching cannot address [1][11].

---

## 3. telemt Internals: FakeTLS at the Byte Level

### ServerHello Construction

telemt's `handshake.rs` implements a two-path ServerHello construction [12]:

- **Path A (tls_emulation cache hit)**: `emulator::build_emulated_server_hello` is called with a `server_hello_template` fetched from the real `mask_host` at startup. This attempts to replicate the actual ServerHello from a legitimate server.
- **Path B (fallback)**: `tls::build_server_hello_with_cipher` is called using `config.censorship.fake_cert_len`. This generates a synthetic ServerHello.

In practice, Path B is always active in 2026: telemt's rustls TLS fetcher is blocked by CDN WAFs, so `tls_emulation` always falls back to the fake cert [1][3]. The fake cert's ServerHello has several fingerprinting-detectable properties:

- **Fixed zero random field**: The ServerHello `random` field is hardcoded to 32 bytes of zeros (`[0]`) [7]. Real TLS 1.3 ServerHellos contain cryptographically random bytes here. This is a trivially matchable DPI signature.
- **Deterministic record sequence**: ServerHello → ChangeCipherSpec → ApplicationData → optional NewSessionTicket-as-ApplicationData, always in this order [7]. Real TLS 1.3 server responses have variable ordering depending on the server implementation.
- **Fixed ChangeCipherSpec count**: Hardcoded to exactly 1 [7].
- **No AEAD tag, no content-type byte**: telemt's `FakeTlsWriter` adds only a 5-byte TLS record header. Real TLS 1.3 Application Data records include a content-type byte and a 16-byte AEAD tag [6]. The absence of these bytes means the Application Data records are structurally non-conformant to TLS 1.3 spec.

### tls_emulation Cache vs Fake Cert

When the cache is populated (Path A), the ServerHello template is borrowed from the real server, which eliminates the zero-random and cipher suite anomalies. However, the Application Data records after the handshake still use telemt's `FakeTlsWriter`, which lacks the AEAD tag. The tls_emulation feature improves handshake-level fingerprint fidelity but does not fix the Application Data layer anomalies that TSPU targets post-handshake.

### The `ee` Prefix and FakeTLS Secret Structure

The `ee` prefix in the proxy secret is a local configuration signal to the Telegram client indicating FakeTLS mode. It is not transmitted on the wire. What the wire sees after the fake TLS handshake is the MTProto Application Data: the first record contains the 64-byte auth key ID, followed by the encrypted MTProto session establishment payload. This payload has high entropy but a specific length distribution and appears immediately after the fake handshake completes — the exact point where mtg issue #547 confirms TSPU intervenes [2].

### `dd` Prefix (Secure/Random Padding Mode)

The `dd` prefix instructs Telegram clients to add random padding to MTProto packets before the FakeTLS wrapper [10]. This increases payload size variance, which partially addresses the record-size-sequence fingerprint. However, it does not change the TLS ClientHello (the JA4 fingerprint issue), does not add AEAD tags to Application Data records, and does not eliminate the fixed zero random field in the ServerHello. Against TSPU's current detection capabilities, `dd` mode provides marginal improvement at best.

### Alternative Transport Modes

telemt v3.4.22 supports exactly three client-facing proxy modes: Classic, Secure (`dd` prefix), and Fake TLS (`ee` prefix + SNI fronting) [4]. There is no support for WebSocket, HTTP/2, XHTTP, TUIC, Hysteria2, or double TLS wrapping [4]. No experimental obfuscation features beyond these three modes are present in the current version. This is not a configuration gap — it is a fundamental architectural constraint of telemt's design.

### telemt Developer Admission (June 5, 2026)

The telemt developers announced on June 5, 2026 that Telegram clients' TLS ClientHello has been banned by JA4/JA4+ fingerprint, and their recommendation for evasion is to build custom Telegram clients using `tdlib-obf` [4]. This is a significant admission: the telemt project's own maintainers have concluded that server-side FakeTLS improvements cannot address the JA4 ClientHello ban, and that client-side modification is required. `tdlib-obf` implements 11 browser TLS ClientHello profiles, dynamic record sizing, inter-packet timing obfuscation via Markov model, and MTProto crypto bucket elimination [13].

---

## 4. Community Findings

### telemt GitHub

- **Issue #653** [14]: telemt stopped working in Russia from April 1, 2026 due to new DPI filtering technologies. This is the first confirmed community report correlating with the April wave.
- **Issue #617** [15]: Telegram handshake timeouts in Russian networks from April 1, 2026, affecting all mobile platforms.
- **Issue #844** [8]: TSPU on MegaFon/MTS specifically inspects the ServerHello packet size (~200–202 bytes) and drops connections where it fits in a single TCP segment. This documents a specific ServerHello-level detection vector that predates the June JA4 wave.
- **README (June 5, 2026)** [4]: Developer announcement of JA4/JA4+ ClientHello ban and tdlib-obf recommendation. This is the clearest statement from the project that server-side FakeTLS has reached its limits.

### mtg (9seconds/mtg) Issue #547

This is the highest-quality external source on TSPU's detection mechanism [2]. It confirms:

1. TSPU analyzes payload after TLS handshake completes, intervening at Application Data start
2. TSPU performs full TCP stream reassembly, defeating fragmentation-based evasion
3. TSPU blocks via silent packet drops (no TCP RST), causing client retransmission loops

The mtg maintainer confirmed as of May–June 2026 that there is no confirmed effective workaround for MTProto inside FakeTLS against TSPU. mtg itself faces the same detection issues as telemt.

### tdesktop Issue #30733 and PR #30513

Telegram Desktop's issue tracker [16] confirms Russian DPI blocking fake-TLS connections starting April 2026. Community PR #30513 identified and corrected ClientHello anomalies (the `0xFE02` extension ID that should be `0xFE0D` for ECH, and a malformed X25519 key field declaring 32 bytes but generating 20 bytes). The PR was merged with minimal changes, but `tdlib` (used by iOS and third-party clients) retains the same errors [17].

### Russian-Language Communities

Community reports from Habr (articles on TSPU detection evolution) indicate:

- TSPU shifted from signature-based to behavioral analysis in February 2026, escalating to "fingerprint freezing" by June 2026
- MTProto proxies are detected and blocked almost immediately after deployment in 2026
- TSPU uses packet blackholing causing ~120-second connection freezes rather than RST/FIN
- VLESS-Reality is reported as the primary working alternative, but requires non-standard clients
- Hetzner AS24940, DigitalOcean, and OVH are explicitly flagged in TSPU's suspicious ASN database

**Research gap**: Direct access to 4pda threads and Telegram channel archives was not available for this report. The Habr findings are secondhand summaries. A direct pull of current 4pda threads on MTProxy working configurations in July 2026 would add signal.

### Academic/Measurement Sources

No Censored Planet, OONI, or ICLab measurements specific to MTProxy endpoints in Russia for June–July 2026 were found in the available evidence. This is a confirmed research gap. Cloudflare's blog on Russian internet access [18] documents general DPI patterns but does not cover MTProxy-specific measurements at the required granularity. The Amnezia shutdown digest for June 2026 [19] confirms the general environment of escalating TSPU blocking but does not provide MTProxy-specific data.

---

## 5. Alternative Approaches Evaluated

### A1: Different Transport for MTProto (WebSocket, HTTP/2, XHTTP)

WebSocket transport for MTProto exists at the protocol level but is not used by Telegram mobile clients as a proxy protocol [4]. Standard Telegram mobile clients only support the `tg://proxy` MTProxy protocol — they do not speak WebSocket or HTTP/2 to proxies. Wrapping MTProto in WebSocket would require a custom client, which violates PRD-001 Non-Goals [5].

Xray's XHTTP transport is a chunked HTTP/1.1 or HTTP/2 transport that wraps arbitrary traffic in HTTP semantics, making it look like a web download stream to DPI. It could theoretically serve as a client-facing layer if the Telegram client could be directed to send its MTProto traffic through an XHTTP-speaking local proxy. However, this requires either a custom Telegram client or a local proxy application on the user's device — both excluded by PRD-001 [5]. **PRD compatibility: Conditional only if a mechanism exists to redirect standard Telegram traffic through XHTTP without client modification, which no current evidence supports.**

### A2: VLESS/VMess/Trojan as Client-Facing Protocol

This approach abandons `tg://proxy` links entirely. Users would configure an Xray/v2ray client and point Telegram's SOCKS5 proxy setting at localhost. A Telegram bot could distribute VLESS configs, but the user experience requires installing a separate VPN client application.

**❌ PRD Non-Goal violation**: PRD-001 requires `tg://proxy` link compatibility and prohibits user-side software installation beyond standard Telegram [5]. This approach fundamentally changes the distribution and onboarding model. The PO would need to explicitly revise these Non-Goals to pursue A2.

### A3: WireGuard / AmneziaWG Tunnel

WireGuard UDP is reported throttled by TSPU since early 2026, and TSPU's behavioral detection module deployed May 25, 2026 explicitly targeted WireGuard alongside MTProto and VLESS. AmneziaWG with obfuscation adds junk packets to the WireGuard handshake to defeat fingerprinting, but its current status against the May 2026 TSPU behavioral module is uncertain. WireGuard over TCP (via `udp2raw` or similar) adds complexity and is not tested.

**❌ PRD Non-Goal violation**: PRD-001 prohibits WireGuard/VPN client requirements on user devices [5]. Even if AmneziaWG worked technically, it requires a separate client application.

### A4: Xray tproxy on Client Side

A local Xray instance on the user's device would wrap MTProto in VLESS-Reality before transmission, presenting a clean TLS 1.3 fingerprint to TSPU. This is technically the most effective approach and is essentially what `tdlib-obf` addresses at the client library level.

**❌ PRD Non-Goal violation**: Requires user-side software installation beyond standard Telegram [5]. This is the same class of violation as A2 and A3.

### A5: use_middle_proxy = true with Real ad_tag

The deploy tests were run with `use_middle_proxy = false`. Enabling middle proxy mode with a real `ad_tag` changes Telegram's internal routing for the official proxy program but does not modify the MTProto handshake structure or the TLS ClientHello in any way that affects TSPU detection [1]. The `ad_tag` is an identifier for Telegram's ad revenue sharing program; it has no bearing on the DPI-visible byte patterns.

**Assessment**: Effort is minimal (config change only). The evidence strongly suggests it will not help. Worth testing this week to conclusively rule it out, but the PO should not plan around it succeeding.

**✅ PRD-001 compatible.**

### A6: EU VPS Provider Not Blocked from Russia

Hetzner AS24940 is confirmed blocked [1]. TSPU's suspicious ASN database also includes DigitalOcean and OVH. However, the database is not exhaustive: major CDNs (Cloudflare, Akamai) are generally excluded, and smaller or less-common EU providers (NodeHost Sweden, Scaleway, Oracle Cloud free tier) may not yet be flagged.

If a non-blocked EU IP is found, direct telemt (no tunnel) might work briefly. However, the June 5, 2026 JA4/JA4+ ClientHello ban means that even a non-blocked IP would not address the ClientHello fingerprint detection. The connection would still be blocked at Stage 1 (JA4 matching) before the payload is even inspected. A non-blocked IP is therefore a necessary but insufficient condition for success.

**Assessment**: Worth investigating as a parallel track (IP range audit this week). It does not solve the JA4 problem but eliminates one blocking layer, which could be useful if the JA4 ban is later addressed via a Telegram client update.

**✅ PRD-001 compatible.**

### A7: Multi-Stage TLS Wrapping (Double TLS)

Wrapping MTProto in FakeTLS and then wrapping FakeTLS in another TLS layer would require either modifying telemt's source code or placing a TLS-terminating proxy in front of it. telemt has no built-in support for double TLS [4].

Even if implemented, TSPU's full TCP stream reassembly would reassemble the outer TLS stream. If the outer TLS is legitimate (real cert, real SNI, real fingerprint), TSPU would need to decrypt it to see the inner FakeTLS layer — which passive DPI cannot do. This is the theoretical argument for double TLS. However, there is no confirmed precedent for this defeating TSPU in the available evidence. The outer TLS layer would also need a non-suspicious ClientHello fingerprint (i.e., not the Telegram JA4 hash), which means it cannot be the standard Telegram client generating the outer TLS — again requiring client-side modification.

**Assessment**: Theoretically interesting but requires telemt source modification and has no confirmed precedent. Insufficient evidence to recommend. **✅ PRD-001 compatible in principle** (no user-side changes required if implemented server-side), but requires Architect evaluation of telemt modification feasibility.

### Summary Table

| Alternative             | Technical Feasibility                                                      | Effort      | PRD-001 Compatible                               | Recommended?                 |
| ----------------------- | -------------------------------------------------------------------------- | ----------- | ------------------------------------------------ | ---------------------------- |
| A1: WebSocket/XHTTP     | Low — standard Telegram clients don't speak WebSocket/XHTTP to proxies     | High        | ❌ Requires custom client                        | No (without PRD revision)    |
| A2: VLESS client-facing | High — technically works                                                   | Medium      | ❌ Non-Goal (no tg://proxy, requires VPN client) | No (without PRD revision)    |
| A3: WireGuard/AmneziaWG | Medium — WG UDP throttled; AmneziaWG status uncertain                      | Medium      | ❌ Non-Goal (VPN client required)                | No (without PRD revision)    |
| A4: Client-side tproxy  | High — effectively what tdlib-obf does                                     | Medium      | ❌ Non-Goal (user-side install required)         | No (without PRD revision)    |
| A5: ad_tag middle proxy | Low probability of success — ad_tag doesn't change DPI-visible patterns    | Low         | ✅                                               | Test to rule out             |
| A6: Non-blocked EU IP   | Partial — removes ASN signal but not JA4 signal                            | Low (audit) | ✅                                               | Yes, as parallel track       |
| A7: Double TLS          | Speculative — no confirmed precedent vs TSPU; requires telemt modification | High        | ✅ (server-side only)                            | Insufficient evidence; defer |

---

## 6. Recommendations

### Immediate (test this week)

**A5: Enable ad_tag + use_middle_proxy**: Change `use_middle_proxy = false` to `true` and configure a real `ad_tag`. Effort: ~1 hour. Expected outcome: no change based on evidence [1], but this conclusively closes the question for the PO.

**A6: EU ASN audit**: Systematically test reachability from Russian ISPs (MTS, Beeline, MegaFon, Rostelecom) to a set of EU providers not currently in use: NodeHost (Sweden), Scaleway (France), Oracle Cloud (Amsterdam), Hetzner alternatives. Method: deploy a simple TCP listener on port 443 on each candidate provider and attempt connection from a Russian residential connection. If a non-blocked ASN is found, deploy telemt there directly (no tunnel) and test. This does not solve the JA4 problem but eliminates the ASN blocking layer and provides a cleaner baseline for further testing.

### Medium Effort (2–4 weeks, pending PRD decision)

**XHTTP transport feasibility spike**: Determine whether Xray's XHTTP transport can serve as a client-facing layer for MTProxy without requiring a custom Telegram client. Specifically: can a Telegram client be directed to use XHTTP by configuring a local SOCKS5 proxy that translates between MTProxy and XHTTP? This requires a technical spike by the Architect. If feasible within PRD constraints, this is the most promising PRD-compatible path.

### Abandon

**All FakeTLS tuning variants**: Cert quality, SNI matching, relay configuration, PROXYv1/v2 selection, domain selection, `tls_emulation` tuning. Nine variants across all these dimensions have been tested and all failed [1][11]. The evidence is conclusive that these server-side parameters do not affect TSPU's detection of the Telegram client's JA4 fingerprint or the MTProto payload patterns. Further testing in this space is not justified.

### Blocking PRD Decision Required

The telemt developers' own recommendation as of June 5, 2026 is `tdlib-obf` — a custom Telegram client that randomizes the TLS ClientHello across 11 browser profiles and obfuscates MTProto traffic patterns [13][4]. This directly conflicts with PRD-001 Non-Goal prohibiting building or distributing custom Telegram clients [5]. This is not a technical recommendation — it is a product decision that only the PO can make.

The PO must decide: **Revise the tdlib-obf Non-Goal, or accept that telemt-mgmt cannot work from Russia without VPN under current PRD constraints.** There is no server-side-only path that defeats both the JA4 ClientHello ban and the post-handshake payload analysis simultaneously. The Architect cannot design around this constraint; the PRD must change first.

---

## 7. Impact on telemt-mgmt Architecture

### ARCH-001 Viability

ARCH-001's core assumption — that FakeTLS disguises MTProto well enough to evade TSPU — is directly refuted by the test evidence. The architecture is not viable as-is for the Russia use case [20][1]. The double-hop topology (Xray entry RU → telemt exit EU) was designed to hide the exit server from TSPU; it does not address the client-side JA4 fingerprint or the post-handshake payload patterns that TSPU now targets. The entry server's role in the architecture is to present a VLESS-Reality facade to TSPU — but the Telegram client connecting to the entry server still generates the banned JA4 fingerprint, and the MTProto Application Data still flows through the connection in a TSPU-detectable form.

### ADR-009 (Encrypted, VLESS-Reality)

ADR-009's double-hop approach correctly identified that the entry segment needs a different transport than the exit segment [21]. The entry server (RU) running Xray VLESS-Reality is the right direction — VLESS-Reality presents a legitimate TLS 1.3 connection to TSPU. The failure is that the **Telegram client's** connection to the entry server still uses the MTProxy protocol with a banned JA4 fingerprint. ADR-009 can be salvaged if the client-facing transport on the entry server is changed to something that does not expose the Telegram JA4 fingerprint. However, this requires either a different client-facing protocol (which needs client-side support) or a client that generates a different fingerprint (tdlib-obf). Without resolving the PRD Non-Goal, ADR-009's entry segment cannot be fixed.

### PRD-001 Non-Goals as Blockers

The most technically viable paths — tdlib-obf (A4) and client-side Xray (A4 variant) — are explicitly excluded by PRD-001 Non-Goals [5]. The PRD also prohibits WireGuard/VPN client requirements (A3) and requires `tg://proxy` link compatibility (ruling out A2). This leaves only A5 (low probability of success), A6 (partial mitigation), and A7 (speculative) as PRD-compatible options. None of these can defeat both TSPU detection layers simultaneously under current constraints.

### Project Viability Assessment

Under current PRD constraints (no custom client, no tdlib-obf, `tg://proxy` links required), **the project cannot achieve its stated goal of providing Telegram access from Russia without VPN**. This is not a temporary operational issue — it reflects a fundamental capability gap between what server-side FakeTLS can provide and what TSPU now requires to be defeated. TSPU's JA4 ClientHello ban (June 5, 2026) and post-handshake payload analysis are both client-side signals that server-side architecture cannot address.

The project is viable if and only if the PO revises the Non-Goal prohibiting tdlib-obf. With that revision, the Architect can design a distribution path for a modified Telegram client and update ARCH-001 to reflect the new client-facing transport requirements. Without that revision, the architecture requires replacement, not modification.

---

## Explore Further

**1. IP range audit for non-blocked EU providers**: A systematic test of which EU ASNs are reachable from Russian residential ISPs (MTS, Beeline, MegaFon, Rostelecom) in July 2026. Method: deploy TCP listeners on port 443 across NodeHost (Sweden AS43948), Scaleway (AS12876), Oracle Cloud Amsterdam (AS31898), and Contabo (AS51167), then test reachability from Russian residential connections. A non-blocked ASN unlocks A6 as a near-term partial mitigation and provides a cleaner test baseline for future evasion attempts.

**2. XHTTP transport feasibility study**: Whether Xray's XHTTP transport can serve as a client-facing layer for MTProxy without requiring a custom Telegram client. Specifically: can a local SOCKS5 shim on the user's device (or a Telegram-compatible proxy adapter) translate between the standard MTProxy protocol and XHTTP, such that the connection to the entry server looks like a chunked HTTP download rather than a TLS-wrapped MTProto stream? If this is achievable without a custom Telegram client, it becomes the most promising PRD-compatible alternative and warrants a dedicated Architect spike.

**3. Censored Planet / OONI measurement pull**: A targeted query of June–July 2026 Russia measurements for MTProxy endpoints specifically. The key question is whether TSPU blocking is uniform across all Russian ISPs or whether some ISPs (e.g., smaller regional providers) have not yet deployed the JA4 blocking rules. ISP-specific variation would materially change the prioritization: if 1–2 ISPs are unblocked, a targeted deployment for those ISPs could provide near-term value while the broader architecture question is resolved.

## References

[1] TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md. https://raw.githubusercontent.com/ponkcore/telemt-mgmt/main/docs/knowledge/TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md
[2] TSPU Protocol Detection After Fake-TLS - mtg issue #547. https://github.com/9seconds/mtg/issues/547
[3] TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md. https://github.com/ponkcore/telemt-mgmt/blob/main/docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md
[4] Telemt - MTProxy on Rust + Tokio - GitHub. https://github.com/telemt/telemt
[5] PRD-001-telemt-mgmt.md. https://raw.githubusercontent.com/ponkcore/telemt-mgmt/main/docs/prd/PRD-001-telemt-mgmt.md
[6] telemt/IMPLEMENTATION_PLAN.md at main. https://github.com/telemt/telemt/blob/main/IMPLEMENTATION_PLAN.md
[7] telemt emulator.rs - TLS Front Implementation. https://raw.githubusercontent.com/telemt/telemt/main/src/tls_front/emulator.rs
[8] Fragment only the ServerHello / initial downstream window ... - GitHub. https://github.com/telemt/telemt/issues/844
[9] TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md. https://raw.githubusercontent.com/ponkcore/telemt-mgmt/main/docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md
[10] MTProxy issue #172. https://github.com/TelegramMessenger/MTProxy/issues/172
[11] TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md. https://github.com/ponkcore/telemt-mgmt/blob/main/docs/knowledge/TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md
[12] handshake.rs - telemt/telemt. https://raw.githubusercontent.com/telemt/telemt/main/src/proxy/handshake.rs
[13] tdlib-obf README. https://github.com/telemt/tdlib-obf/blob/master/README.md
[14] telemt issue #653. https://github.com/telemt/telemt/issues/653
[15] [NON-TELEMT] Telegram handshake timeout in Russian networks. https://github.com/telemt/telemt/issues/617
[16] Обновить fingerprint MTPROTO FakeTLS · Issue #30733 - GitHub. https://github.com/telegramdesktop/tdesktop/issues/30733
[17] TLS Fingerprint fixes in MTProxy ClientHello #7746 - GitHub. https://github.com/telegramdesktop/tdesktop/actions/runs/23926842991
[18] Russian Internet users are unable to access the open Internet. https://blog.cloudflare.com/russian-internet-users-are-unable-to-access-the-open-internet/
[19] Amnezia Shutdown Digest June 2026 Russia. https://amnezia.org/en/blog/amnezia-shutdown-digest-june-2026-russia
[20] ARCH-001-telemt-mgmt.md - Architecture Document. https://github.com/ponkcore/telemt-mgmt/blob/main/docs/architecture/ARCH-001-telemt-mgmt.md
[21] TELEMT_TSPU_EVASION_PATTERNS.md. https://raw.githubusercontent.com/ponkcore/telemt-mgmt/main/docs/knowledge/TELEMT_TSPU_EVASION_PATTERNS.md
