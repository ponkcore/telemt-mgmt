# GitHub Ecosystem Catalog: Telemt / MTProto / MTProxy — Comprehensive Reference

**Research date:** 2026-07-02 | **Scope:** 100+ projects across 15 categories (A–O)

---

## Section 1 — Top-20 Projects: Detailed Descriptions

### 1. telemt/telemt ⭐⭐⭐⭐⭐

telemt is the primary production MTProxy server for 2026, written in Rust using the Tokio async runtime [1]. It fully implements all three official Telegram proxy modes: **Classic** (unencrypted, for compatibility), **Secure/dd** (random padding added to packet headers to defeat DPI statistical analysis), and **FakeTLS/ee** (traffic disguised as TLS 1.3 HTTPS with configurable SNI domain, behaviorally consistent with real browser TLS) [1]. As of the research date, it carries 5,418 stars and 246 forks, with the last commit on 2026-06-30 [1].

Configuration is through `config.toml`. Key blocks: `[general]` controls `use_middle_proxy`, `[modes]` enables classic/secure/tls, `[tls]` sets `tls_domain`, `tls_emulation` (fetches real certificate lengths from the SNI target), and `tls_front_dir` cache. `[prometheus]` exposes metrics on port 9090 with IP whitelist. `[[users]]` entries carry per-user `secret` and `ad_tag` (32-hex from @MTProxybot) [2]. Upstream chaining is in `[[upstreams]]` with types `direct`, `socks4`, `socks5`, `shadowsocks` and a `weight` field for load balancing; Shadowsocks upstream requires `use_middle_proxy = false` in `[general]` [3].

Deployment: one-command installer via `curl | bash` [4] with multi-architecture detection (x86_64, x86_64-v3/AVX2, aarch64), glibc/musl libc discrimination, systemd/OpenRC service setup, and interactive prompts for domain, port, secret, and ad_tag [5]. Distroless multi-arch Docker images are also available. Replay attack protection is built in. Traffic masking mode forwards unrecognized connections to a real web server (configurable), making the port indistinguishable from an HTTPS server to passive scanners [1].

Telemt explicitly notes that Telegram client TLS ClientHello was banned via JA4/JA4+ fingerprinting as of June 2026, and directs operators to the companion `tdlib-obf` library for building obfuscated clients [1]. PROXY protocol support is available for HAProxy/nginx deployments [2]. The REST API (`/v1/config`, `/v1/users`) allows runtime user management, though upstream config changes require a process restart [3].

**Limitations:** ad_tag requires `middle_proxy` mode (incompatible with Shadowsocks upstream). No built-in web UI — requires MTProxyMax or a custom panel.

**Verdict:** The only server to use for production in Russia in 2026. All other choices are compromises on features, censorship resistance, or maintenance status.

---

### 2. SamNet-dev/MTProxyMax ⭐⭐⭐⭐⭐

MTProxyMax is a Bash-based management wrapper around the telemt 3.x Rust engine [6]. It adds everything telemt lacks: a TUI dashboard, a full CLI suite, a 21-command Telegram bot, a commercial voucher billing system, master-slave replication, encrypted backups, and Prometheus metrics with per-user granularity [7]. Star count varies between sources: one topic page shows ~620, another ~2,500+; the discrepancy likely reflects different crawl timestamps and the project's rapid growth.

The **Telegram bot** exposes 21 admin commands, including: `/mp_status`, `/mp_users`, `/mp_adduser`, `/mp_remove`, `/mp_disable`, `/mp_limits`, `/mp_setlimit`, `/mp_link` (generates tg://proxy link + QR code), `/mp_voucher`, `/mp_replication`, `/mp_backup`, and more [6]. The **voucher system** generates batch gift codes in `MTP-XXXX-XXXX` format with configurable data quotas and expiry durations, redeemable via CLI or bot [6]. RBAC has Superadmin and Reseller roles [6].

Anti-DPI features added in v1.1.0: FakeTLS V2, Multi-Domain SNI Pool, Kernel SYN Shield (tarpitting DPI scanners), TCP MSS Clamping, Stealth Presets (normal/ultra), and Active DPI Forensics [6]. Upstream proxy configuration supports Cloudflare WARP, backup VPS with authentication, and weight-based routing across multiple SOCKS5 upstreams [6]. The `ping-dc` command benchmarks TCP handshake latency to Telegram DC1–DC5 with fastest-DC detection; `net-grade` calculates an A+/A/B/C quality score based on DNS ping and TCP reachability [6].

Prometheus metrics are exposed on `localhost:9090/metrics` with real per-user traffic stats (bytes uploaded/downloaded, active connections) [6]. A static glassmorphism status portal is included for user-facing config distribution.

**Limitations:** Bash wrapper means telemt engine upgrades require MTProxyMax to track upstream. Voucher system does not process direct payments — operators must distribute codes manually or build a payment→voucher bridge. No native payment gateway integration.

**Verdict:** The single most time-saving project for anyone running a multi-user telemt instance. Install telemt first, then MTProxyMax on top.

---

### 3. 9seconds/mtg ⭐⭐⭐⭐

mtg is a Go-based MTProxy implementation with 3,599 stars, last committed 2026-06-11 [8]. It is designed for high concurrency — the author targets 10–20k simultaneous connections — and deliberately keeps the feature set minimal ("highly opinionated"). Modes: Classic and FakeTLS/ee with Domain Fronting (configurable SNI masking). Prometheus/Statsd metrics are built in with configurable namespace [8].

**v1 vs v2 split:** v2 explicitly removed ad_tag support, which the author argues improves security and reduces attack surface [8]. If ad_tag monetization is a requirement, use telemt or mtg v1 only. v2 supports Proxy Protocol v1/v2 for load balancers, configurable IPv4/IPv6 upstream preference, IP blocklists/allowlists, and domain fronting with SNI masking [8].

Upstream chaining: mtg supports routing through SOCKS5 proxies and can be fronted by v2ray, Gost, Trojan, or Shadowsocks [8]. Secret generation: `mtg generate-secret` outputs Base64 or hex secrets with `ee` prefix for FakeTLS mode [8].

**Grafana dashboard:** ID 11904 ("Telegram MTProto Proxy Status") is available on Grafana Labs for mtg-based deployments.

**Limitations:** No ad_tag in v2. No multi-user per-secret management. No built-in web UI.

**Verdict:** Good alternative to telemt for resource-constrained servers or when monetization is not needed. Not recommended as primary choice for Russian operators who need ad_tag.

---

### 4. TelegramMessenger/MTProxy ⭐⭐⭐

The official C-based MTProxy from Telegram Messenger. Star count varies across sources — evidence shows 6,867 [9], ~8k [from another crawl], and ~2,000+ [from a third] — the discrepancy reflects different forks being indexed and different crawl dates. The canonical repo at `github.com/TelegramMessenger/MTProxy` had its last commit on 2025-11-04 [9].

**Why not for production in Russia:** No FakeTLS support. Requires manual daily download of `proxy-multi.conf` from `core.telegram.org` [9]. No upstream proxy chaining (open issue #143 and #672 are unresolved) [1]. Requires building from source with openssl/zlib dev packages [9].

**Historical value:** The reference implementation for the MTProto proxy wire protocol. All other implementations conform to its behavior. The `dd`-prefix secret mechanism (random padding to defeat DPI) was documented in its issue #172 [1]. Secret generation: `head -c 16 /dev/urandom | xxd -ps` [1].

**Verdict:** Do not deploy in production in Russia. Use as protocol reference or for testing Classic mode compatibility.

---

### 5. telemt/tdlib-obf ⭐⭐⭐⭐⭐

tdlib-obf is a security-hardened fork of the official TDLib (C++23), maintained by the telemt team, with ~131–400 stars depending on crawl date [10]. It solves the JA4/JA4+ fingerprint ban: standard Telegram clients emit a distinctive TLS ClientHello that Russian DPI systems began blocking in June 2026. tdlib-obf replaces the ClientHello with one derived from real-world PCAP captures of actual browsers [10].

**Technical mechanism:** 11 browser profiles covering Chrome 131/133/147, Firefox 148/149, Safari 26.3, iOS 14, and Android OkHttp. Each profile reproduces the exact cipher suite order, extensions, GREASE values, and ML-KEM-768 post-quantum key shares from real browser traffic [10]. Dynamic Record Sizing (DRS) adjusts TLS record boundaries to match browser patterns. Inter-Packet Timing Obfuscation (IPT) adds statistical noise to packet intervals [10]. Route-Aware ECH (Encrypted Client Hello) with circuit breaker handles ECH failures gracefully.

**Integration with telemt:** Stealth mode activates **only** when the client connects through an MTProto proxy with a `0xee`-prefixed secret (FakeTLS mode). Direct connections use standard TDLib behavior [10]. Build requirement: `cmake -DTDLIB_STEALTH_SHAPING=ON` and `zlib >= 1.3.2` (CVE-2026-22184 patch required) [10].

**Usage:** App developers building custom Telegram clients (Android, Desktop) replace the standard TDLib dependency with tdlib-obf. The integration guide is at `github.com/telemt/tdlib-obf/blob/master/docs/Documentation/CUSTOM_CLIENT_INTEGRATION_GUIDE.md` [11].

**Limitations:** Requires building a custom Telegram client — not a drop-in for end users. No pre-built APKs distributed by the telemt team.

**Verdict:** Critical for operators whose users are experiencing JA4-based blocking. Without this, FakeTLS on the server side alone is insufficient if the client's TLS fingerprint is already flagged.

---

### 6. sleep3r/mtproto.zig ⭐⭐⭐⭐

mtproto.zig is a dependency-free MTProxy server written in Zig with ~1,086–1,100 stars, last committed 2026-06-15. Binary size: 177 KB. RAM usage: under 1 MB in proxy-only mode (the embedded web dashboard adds ~30 MB) [6].

**Upstream support:** config.toml supports modes `auto`, `direct`, `tunnel`, `socks5`, `http`, and VLESS links with REALITY security — making it the only MTProxy server with native VLESS/REALITY upstream [1]. Designed explicitly for bypassing Russian TSPU DPI. FakeTLS 1.3 masking, TCP desynchronization, and IPv6 hopping are built in.

**Monitoring:** Embedded web dashboard at `127.0.0.1:61208` (HTTP Basic auth) shows live connections, CPU/memory, network throughput, proxy stats, and tunnel pool health. Prometheus metrics endpoint on port 9409. Docker-based monitoring stack with Prometheus + Grafana is provided in the repo.

**Secret generation:** `mtbuddy secret` command generates `ee`-prefixed secrets.

**Limitations:** Zig ecosystem is less mature than Rust/Go for production ops. No ad_tag support. No multi-user per-secret management comparable to telemt.

**Verdict:** Best choice for embedded/IoT (OpenWRT, low-RAM VPS) or when VLESS/REALITY upstream is needed natively without chaining.

---

### 7. spyrae/ProxyCraft ⭐⭐⭐⭐⭐ (for monetization)

ProxyCraft is a complete VPN/proxy service sold through a Telegram bot, with MTProxy support via `alexbers/mtprotoproxy` Docker container [12]. Payment gateways: Telegram Stars, YooKassa, YooMoney, T-Bank, Cryptomus, and Heleket (crypto) [13]. Referral system: 2-level with +30 days (L1 referrer) / +3 days (L2 referrer) / +7 days bonus for the referred user on first payment [12].

**Architecture:** The Telegram bot handles the full sales funnel — subscription selection, payment, automatic secret provisioning, and renewal notifications. The MTProxy backend runs as a Docker container. The referral system is built in, not bolted on.

**Limitations:** MTProxy backend uses `alexbers/mtprotoproxy` (Python, not telemt), which lacks FakeTLS in its standard form. For Russian operators, this means the DPI resistance layer is weaker than telemt. Replacing the backend with telemt requires custom integration work.

**Verdict:** The most complete off-the-shelf monetization solution for MTProxy. Use it as-is if DPI resistance is not the primary concern, or adapt the payment/bot layer while replacing the proxy backend with telemt.

---

### 8. LonamiWebs/Telethon ⭐⭐⭐⭐

Telethon is a pure-Python 3 asyncio MTProto library with ~12,000 stars, last updated February 2026 [12]. It implements the full MTProto 2.0 protocol natively (not a TDLib wrapper), including MTProxy support. Used for building Telegram bots, user-account automation, and management tools.

**Integration with telemt:** Telethon is the library used inside telemt's own `tools/dc.py` to fetch DC configuration via `GetConfigRequest` [14]. Any management panel built in Python (bot for user CRUD, stats scraping, config distribution) should use Telethon.

**Limitations:** Python GIL limits raw throughput for high-concurrency proxy servers. Not suitable as a proxy server itself — use for tooling around telemt.

---

### 9. tdlib/td ⭐⭐⭐⭐

Official TDLib from Telegram, C++17, with ~7,200–8,900 stars depending on crawl [15]. Supports 20+ operating systems including Android, iOS, Windows, macOS, Linux, FreeBSD, WebAssembly, and more [15]. Native JNI bindings for Java and C++/CLI bindings for.NET [15]. Full MTProto 2.0 with proxy support.

**Role in the ecosystem:** The reference client library. tdlib-obf is a fork of this. Any custom Telegram client not using tdlib-obf will expose the standard TDLib TLS fingerprint.

---

### 10. XTLS/Xray-core ⭐⭐⭐⭐

Xray-core is a Go-based network proxy framework with 40,013 stars, last commit 2026-07-01 [13]. Protocols: VLESS, VMess, Trojan, Shadowsocks, REALITY (TLS impersonation using a real server's certificate), XHTTP, and uTLS integration.

**Integration with telemt:** Used as a SOCKS5 upstream in telemt's `[[upstreams]]` section. Configure Xray to listen on a local SOCKS5 port with REALITY or VLESS outbound, then point telemt's upstream at `socks5://127.0.0.1:PORT`. This creates the chain: Telegram client → telemt (FakeTLS) → Xray (REALITY) → Telegram DC. The REALITY layer provides a second TLS layer that impersonates a real domain, making the upstream connection undetectable.

**Limitations:** No direct MTProto proxy mode — Xray is always an upstream transport layer, not a replacement for telemt.

---

### 11. SagerNet/sing-box ⭐⭐⭐⭐

sing-box is a universal proxy platform in Go with 35,579 stars, last commit 2026-07-01 [16]. Supports Shadowsocks, VLESS, VMess, Trojan, Hysteria2, TUIC, NaiveProxy, WireGuard, and more. Can function as a SOCKS5 or Shadowsocks server that telemt chains through.

**Integration with telemt:** Run sing-box as a local SOCKS5 or Shadowsocks outbound, configure telemt's `[[upstreams]]` to route through it. sing-box can then forward traffic via VLESS+REALITY, Hysteria2, or any other protocol to exit near the Telegram DCs.

---

### 12. Hiddify-Manager ⭐⭐⭐

Hiddify is a multi-user anti-filtering panel supporting 20+ protocols including MTProxy (using telemt as backend). Stars: ~15,000+. It has native MTProxy support with known iOS Telegram client compatibility issues (reported in issue #4623). No direct payment gateway integration for MTProxy specifically — billing requires a separate bot layer.

**Marzban, Marzneshin, 3x-ui verdict:** These panels do **not** support MTProxy protocol — they are Xray-core based only. Do not attempt MTProxy integration with these panels without significant custom development.

---

### 13. refraction-networking/utls ⭐⭐⭐⭐

utls is a Go library that provides ClientHello fingerprint resistance for TLS connections. It allows Go programs to impersonate specific browser TLS fingerprints (Chrome, Firefox, Safari, etc.) by replacing the standard `crypto/tls` ClientHello with a pre-configured browser profile. Used by Xray-core, sing-box, and other proxy tools for REALITY and uTLS transport.

**Integration with telemt:** Not a direct upstream — utls is a library used inside Go-based proxy tools (Xray, sing-box, mtg) that telemt chains through. If building a custom Go-based upstream for telemt, use utls for TLS fingerprint spoofing.

---

### 14. bogdanfinn/tls-client ⭐⭐⭐

tls-client (1,709 stars, last commit 2026-06-08) provides a `net/http.Client` with selectable TLS fingerprints for Go. Useful for building HTTP scrapers or API clients that need to pass TLS fingerprint checks. Less directly relevant to MTProxy server operations than utls, but useful for building management tools that call Telegram APIs through specific fingerprints.

---

### 15. ginuerzh/gost ⭐⭐⭐⭐

GOST (GO Simple Tunnel) has ~18,100 stars and supports HTTP, HTTPS, SOCKS4/5, Shadowsocks, WireGuard, and chain proxy building with random parent selection for load distribution. Can serve as a SOCKS5 upstream for telemt or as a multi-hop relay.

**Integration with telemt config.toml:**

```toml
[[upstreams]]
type = "socks5"
address = "127.0.0.1:1080"
weight = 10
```

Run gost with: `gost -L socks5://:1080 -F ss://aes-256-cfb:password@exit-server:8388`

---

### 16. gotd/td ⭐⭐⭐

gotd/td is a pure Go MTProto API client with explicit MTProxy support [17]. Useful for building management bots, stats collectors, or automation tools in Go. Lower-level than Telethon but type-safe and idiomatic Go.

---

### 17. pyrogram/pyrogram ⭐⭐⭐

Pyrogram is a modern async Python MTProto framework (~4,600 stars). Alternative to Telethon for building bots and automation. Both libraries can be used for telemt management tooling; Telethon has a larger community and more examples for DC-level operations.

---

### 18. HirbodBehnam/MTProtoProxyInstaller ⭐⭐⭐

One-click bash installer for MTProxy on CentOS, Ubuntu, and Debian. Installs the official TelegramMessenger/MTProxy binary with automated firewall configuration and systemd service setup. Generates random secrets with `dd`-prefix support and FakeTLS links beginning with `ee` [1]. Includes post-install API support.

**Verdict:** Use only if you specifically need the official C-based proxy for compatibility testing. For production, telemt's own `install.sh` is more capable.

---

### 19. gram-js/gramjs ⭐⭐⭐

GramJS is a JavaScript/TypeScript MTProto client (Node.js and browser) with a core based on Telethon. Useful for building web-based management panels or bots in JavaScript. Supports MTProxy connections. Active development as of 2026.

---

### 20. Grafana Dashboard ID 25119 — Telemt Proxy Health ⭐⭐⭐⭐

Purpose-built Grafana dashboard for telemt, published 2026-04-06, requires Grafana 12.4.2+. Panels cover: uptime, active connections, traffic (bytes in/out), upstream health, security events (replay attacks, blocked IPs), and per-user bandwidth breakdown. Integrates directly with telemt's Prometheus endpoint on port 9090. Import via Grafana dashboard ID `25119` or from `grafana.com/grafana/dashboards/25119-telemt-proxy-health/`.

---

## Section 2 — Category A: MTProxy Server Implementations

| Project                   | URL                                  | Lang    | ★      | Last Commit | Status      | Modes           | Multi-user         | Ad-tag         | Masking                           | API        | Monitoring                      | Docker           | Notes                                           | Compat w/ telemt | Rating     |
| ------------------------- | ------------------------------------ | ------- | ------ | ----------- | ----------- | --------------- | ------------------ | -------------- | --------------------------------- | ---------- | ------------------------------- | ---------------- | ----------------------------------------------- | ---------------- | ---------- |
| telemt/telemt             | [1]                                  | Rust    | 5,418  | 2026-06-30  | Active      | Classic/dd/ee   | Yes (per-secret)   | Yes            | FakeTLS+SNI, traffic mask         | REST /v1   | Prometheus                      | Yes (distroless) | Load balancer PROXY protocol; replay protection | Native           | ⭐⭐⭐⭐⭐ |
| TelegramMessenger/MTProxy | [9]                                  | C       | 6,867  | 2025-11-04  | Legacy      | Classic/dd      | No                 | Yes            | None                              | Stats:8888 | Built-in stats                  | Yes (official)   | Requires daily conf update                      | Reference only   | ⭐⭐⭐     |
| 9seconds/mtg              | [8]                                  | Go      | 3,599  | 2026-06-11  | Active      | Classic/ee (v2) | No                 | v1 only        | FakeTLS+domain fronting           | None       | Prometheus/Statsd               | Yes              | 10–20k connections; v2 dropped ad_tag           | As upstream      | ⭐⭐⭐⭐   |
| sleep3r/mtproto.zig       | github.com/sleep3r/mtproto.zig       | Zig     | ~1,100 | 2026-06-15  | Active      | Classic/ee      | No                 | No             | FakeTLS 1.3, TCP desync, IPv6 hop | None       | Embedded dashboard + Prometheus | Yes              | 177KB binary, <1MB RAM; VLESS/REALITY upstream  | As upstream      | ⭐⭐⭐⭐   |
| alexbers/mtprotoproxy     | [18]                                 | Python  | ~1,000 | 2023        | Maintenance | Classic/dd/ee   | Yes (multi-port)   | Yes            | FakeTLS                           | None       | None                            | Yes              | ~4,000 users/1 CPU core/1GB RAM                 | Via Docker       | ⭐⭐⭐     |
| seriyps/mtproto_proxy     | github.com/seriyps/mtproto_proxy     | Erlang  | ~700   | 2024        | Maintenance | Classic/dd/ee   | Yes (multi-port)   | Yes (per-port) | FakeTLS                           | None       | None                            | Yes              | Hot reload without restart; OTP supervision     | No               | ⭐⭐⭐     |
| teleproxy/teleproxy       | [19]                                 | Go      | ~200   | 2024        | Maintenance | Classic/ee      | Yes                | No             | FakeTLS, probe resistance         | None       | Prometheus                      | Yes              | Per-user analytics                              | No               | ⭐⭐⭐     |
| scratch-net/telego        | [20]                                 | Go      | ~100   | 2023        | Maintenance | Classic/ee      | Yes                | No             | TLS fronting                      | None       | None                            | No               | Per-user analytics                              | No               | ⭐⭐⭐     |
| FreedomPrevails/JSMTProxy | github.com/FreedomPrevails/JSMTProxy | Node.js | ~92    | 2019        | Abandoned   | Classic         | No                 | No             | None                              | None       | None                            | No               | Requires Node.js 6+                             | No               | ⭐         |
| makkarpov/mtoxy           | github.com/makkarpov/mtoxy           | Java    | ~50    | 2018-05-30  | Abandoned   | Classic         | No                 | No             | HTTP passthrough                  | None       | None                            | No               | Proxy chaining; HTTP bypass on port 80          | No               | ⭐⭐       |
| dotcypress/mtproxy        | github.com/dotcypress/mtproxy        | Rust    | ~233   | 2018-06-14  | Abandoned   | Classic         | No                 | No             | None                              | None       | None                            | Yes              | mio-powered; WIP at abandonment                 | No               | ⭐         |
| skrashevich/MTProxy       | github.com/skrashevich/MTProxy       | Go      | ~0     | 2026-07-01  | Active      | Classic         | No                 | No             | None                              | None       | None                            | No               | Go port of official C proxy                     | No               | ⭐⭐       |
| RustedBytes/mtproxy       | github.com/RustedBytes/mtproxy       | Rust    | ~30    | 2022        | Abandoned   | Classic         | No                 | No             | None                              | None       | None                            | No               | Experimental C→Rust translation                 | No               | ⭐         |
| yiiman-dev/MTProxy        | github.com/yiiman-dev/MTProxy        | C       | ~20    | 2022        | Abandoned   | Classic/dd      | Yes (multi-secret) | Yes            | None                              | None       | None                            | No               | Fork of official with up to 16 secrets          | No               | ⭐⭐       |

**Commentary for Russia 2026:** Only telemt and mtproto.zig are production-ready for the Russian DPI environment. mtg v2 is viable if ad_tag is not needed. The official C proxy and all pre-2020 implementations lack FakeTLS and should not be deployed where DPI blocking is active. The Erlang implementation (seriyps) has the unique advantage of hot reload without restart — worth forking if per-port ad_tag management is needed. JSMTProxy, mtoxy, and dotcypress/mtproxy are dead; their ideas (HTTP passthrough, proxy chaining) have been absorbed into telemt.

---

## Section 3 — Category B: Management Panels, Wrappers, Admin Tools

| Project                            | URL                                           | Type                   | Server     | Lang       | ★           | Status      | Functions                                                         | Multi-user                  | Monitoring      | Billing                   | Replication  | Backups   | Auto-update | Rating     |
| ---------------------------------- | --------------------------------------------- | ---------------------- | ---------- | ---------- | ----------- | ----------- | ----------------------------------------------------------------- | --------------------------- | --------------- | ------------------------- | ------------ | --------- | ----------- | ---------- |
| SamNet-dev/MTProxyMax              | [6]                                           | TUI+CLI+Bot+Portal     | telemt 3.x | Bash+Rust  | ~620–2,500+ | Active      | CRUD users, stats, billing, ad-tag, geo-block, DPI presets        | Yes (per-user quotas, RBAC) | Prometheus:9090 | Voucher system (MTP-XXXX) | Master-slave | Encrypted | Yes         | ⭐⭐⭐⭐⭐ |
| danielVNru/mtproto-panel           | [21]                                          | Web (React+Express+PG) | Any        | TS+Node.js | ~50         | Active      | Multi-node, VLESS tunnel, IP blacklist, FakeTLS pool (50 domains) | Yes                         | None built-in   | None                      | Multi-node   | None      | No          | ⭐⭐⭐⭐   |
| Therealwh/MTProtoSERVER            | github.com/Therealwh/MTProtoSERVER            | Web+Bot                | Any        | Unknown    | ~30         | Active      | Multi-node, FakeTLS, SOCKS5, 2FA, real-time monitoring            | Yes                         | Built-in        | Referral only             | Yes          | No        | No          | ⭐⭐⭐     |
| Arjun99291/telemt-panel            | github.com/Arjun99291/telemt-panel            | Web                    | telemt     | Unknown    | ~10         | Active      | Create/monitor/manage FakeTLS instances                           | Yes                         | Basic           | None                      | No           | No        | No          | ⭐⭐       |
| telemt install.sh                  | [4]                                           | CLI installer          | telemt     | Bash       | —           | Active      | Install/uninstall/update, arch detect, ad_tag, TLS config         | No                          | No              | No                        | No           | No        | Yes         | ⭐⭐⭐⭐⭐ |
| HirbodBehnam/MTProtoProxyInstaller | github.com/HirbodBehnam/MTProtoProxyInstaller | CLI installer          | Official C | Bash       | ~500        | Maintenance | One-click install CentOS/Ubuntu, firewall, systemd                | No                          | No              | No                        | No           | No        | No          | ⭐⭐⭐     |
| missuo/MTProxy                     | github.com/missuo/MTProxy                     | CLI installer          | Official C | Bash       | ~200        | Maintenance | Claims "v2" vs v1 scripts                                         | No                          | No              | No                        | No           | No        | No          | ⭐⭐       |
| statix05/MTProxyInstall            | github.com/statix05/MTProxyInstall            | Docker installer       | Official C | Bash       | ~100        | Maintenance | Docker-based, watchdog                                            | No                          | No              | No                        | No           | No        | No          | ⭐⭐       |
| cimon-io/ansible-role-mtproxy      | github.com/cimon-io/ansible-role-mtproxy      | Ansible role           | Official C | Ansible    | ~30         | Maintenance | Configurable version/repo                                         | No                          | No              | No                        | No           | No        | No          | ⭐⭐⭐     |
| iShift/docker-compose-mtproxy      | github.com/iShift/docker-compose-mtproxy      | Docker Compose         | Official C | YAML       | ~20         | Maintenance | Watchdog for auto-update                                          | No                          | No              | No                        | No           | No        | Yes         | ⭐⭐       |

**MTProxyMax star discrepancy explained:** GitHub topic pages are crawled at different times. The range 620–2,500+ reflects the project's active growth between crawl windows. The higher number is more likely current given the project's feature set and activity.

**mtproto-panel architecture:** Three Docker containers — frontend (Nginx+React), backend (Express API port 3000), database (PostgreSQL port 5432), installed to `/opt/mtproto-panel`. Each proxy server runs a separate `mtproto-node` agent controlled by the central panel [21]. Supports Ubuntu 20.04–24.04, Debian 11–12, CentOS/RHEL 8–9, x86_64 and aarch64 only [21].

---

## Section 4 — Category C: Telegram Bots for Proxy Management

| Project                                | URL                                   | Commands                                                                                                                                                                                                                                                                  | Server        | Auto-links       | Billing       | Notifications       | Lang  | Rating     |
| -------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ---------------- | ------------- | ------------------- | ----- | ---------- |
| MTProxyMax bot (built into MTProxyMax) | [6]                                   | /mp_status, /mp_users, /mp_adduser, /mp_remove, /mp_disable, /mp_enable, /mp_limits, /mp_setlimit, /mp_link (QR), /mp_voucher, /mp_replication, /mp_backup, /mp_adtag, /mp_upstream, /mp_dpi, /mp_logs, /mp_restart, /mp_update, /mp_grade, /mp_ping, /mp_help (21 total) | telemt 3.x    | Yes (tg:// + QR) | Voucher codes | Quota/expiry alerts | RU+EN | ⭐⭐⭐⭐⭐ |
| @MTProxybot (official Telegram bot)    | t.me/MTProxybot                       | /start, register proxy, get ad_tag                                                                                                                                                                                                                                        | Any           | No               | No            | None                | EN    | ⭐⭐⭐⭐   |
| mmdzov/mtproxybot                      | github.com/mmdzov/mtproxybot          | /start, /reset                                                                                                                                                                                                                                                            | Any           | No               | No            | None                | EN    | ⭐         |
| MT-proxy-bot-SG                        | github.com/thejan64go/MT-proxy-bot-SG | /start, /list, /get                                                                                                                                                                                                                                                       | Public list   | Yes              | No            | None                | EN    | ⭐⭐       |
| MTProtoSERVER bot                      | github.com/Therealwh/MTProtoSERVER    | Full management                                                                                                                                                                                                                                                           | MTProtoSERVER | Yes              | Referral      | Yes                 | RU    | ⭐⭐⭐     |

**Key finding:** Only MTProxyMax's bot combines billing (vouchers), auto-link generation with QR codes, and full user lifecycle management. @MTProxybot is mandatory for ad_tag registration but does nothing else. mmdzov/mtproxybot is inactive (last commit January 2024, 2 stars) and covers only basic status. For Russian operators, MTProxyMax's bot is the only production-ready option.

---

## Section 5 — Category D: MTProto Client Libraries

| Project                   | URL                                  | Lang        | Implements                | MTProxy       | TDLib?   | ★            | Status           | Docs              | Rating     |
| ------------------------- | ------------------------------------ | ----------- | ------------------------- | ------------- | -------- | ------------ | ---------------- | ----------------- | ---------- |
| tdlib/td                  | [15]                                 | C++         | Full MTProto 2.0 + client | Yes           | IS TDLib | ~7,200–8,900 | Active           | Excellent         | ⭐⭐⭐⭐⭐ |
| telemt/tdlib-obf          | [10]                                 | C++         | TDLib + DPI obfuscation   | Yes (ee only) | Fork     | ~131–400     | Active           | Integration guide | ⭐⭐⭐⭐⭐ |
| LonamiWebs/Telethon       | [12]                                 | Python      | Native MTProto 2.0        | Yes           | No       | ~12,000      | Active           | Excellent         | ⭐⭐⭐⭐⭐ |
| pyrogram/pyrogram         | github.com/pyrogram/pyrogram         | Python      | Native MTProto            | Yes           | No       | ~4,600       | Active           | Good              | ⭐⭐⭐⭐   |
| gotd/td                   | [17]                                 | Go          | Native MTProto            | Yes           | No       | ~2,000       | Active           | Good              | ⭐⭐⭐⭐   |
| gram-js/gramjs            | github.com/gram-js/gramjs            | JS/TS       | Native MTProto            | Yes           | No       | ~3,000       | Active           | Good              | ⭐⭐⭐⭐   |
| aiogram/aiogram           | github.com/aiogram/aiogram           | Python      | Bot API only              | Via Bot API   | No       | ~10,000      | Active           | Excellent         | ⭐⭐⭐     |
| wiz0u/WTelegramClient     | github.com/wiz0u/WTelegramClient     | C#          | Full MTProto 2.0          | Yes           | No       | ~2,500       | Active           | Good              | ⭐⭐⭐⭐   |
| danog/MadelineProto       | github.com/danog/madelineproto       | PHP         | Native MTProto            | Yes           | No       | ~3,000       | Active           | Good              | ⭐⭐⭐     |
| badoualy/kotlogram        | github.com/badoualy/kotlogram        | Java/Kotlin | MTProto bindings          | Unknown       | No       | ~500         | Maintenance      | Basic             | ⭐⭐       |
| Telegram4J/Telegram4J     | github.com/Telegram4J/Telegram4J     | Java        | Reactive MTProto          | Unknown       | No       | ~200         | Active           | Basic             | ⭐⭐       |
| peter-iakovlev/MtProtoKit | github.com/peter-iakovlev/MtProtoKit | Swift       | MTProto for iOS/macOS     | Yes           | No       | ~200         | Abandoned (2019) | Minimal           | ⭐⭐       |
| mtcute (TypeScript)       | github.com/mtcute/mtcute             | TS          | Native MTProto            | Yes           | No       | ~500         | Active           | Good              | ⭐⭐⭐⭐   |

**Note on aiogram:** aiogram is a Bot API framework, not an MTProto library. It communicates with Telegram's Bot API server over HTTPS, not directly via MTProto. It cannot be used for user-account operations or DC-level tooling.

**Library recommendation for building a telemt management panel:**

- **Python:** Telethon. It is used inside telemt's own tooling, has the largest community, and handles DC-level operations (GetConfigRequest, etc.) cleanly. Pyrogram is an equally valid alternative with a slightly more modern API.
- **Go:** gotd/td. Type-safe, idiomatic Go, explicit MTProxy support [17].
- **JavaScript/TypeScript:** GramJS (broader community) or mtcute (more modern, multi-runtime including Deno and Bun).

---

## Section 6 — Category E: DPI Bypass and Traffic Masking Tools

| Project                      | URL                                     | Type                                  | MTProto link            | How to use with telemt                                                     | ★       | Status               | Rating     |
| ---------------------------- | --------------------------------------- | ------------------------------------- | ----------------------- | -------------------------------------------------------------------------- | ------- | -------------------- | ---------- |
| XTLS/Xray-core               | [13]                                    | Proxy framework (VLESS/REALITY/XHTTP) | Indirect (upstream)     | SOCKS5 upstream in [[upstreams]]; Xray exits via REALITY                   | 40,013  | Active               | ⭐⭐⭐⭐⭐ |
| SagerNet/sing-box            | [16]                                    | Universal proxy platform              | Indirect (upstream)     | SOCKS5 or SS upstream; sing-box exits via VLESS/Hysteria2/TUIC             | 35,579  | Active               | ⭐⭐⭐⭐⭐ |
| v2fly/v2ray-core             | github.com/v2fly/v2ray-core             | Proxy framework                       | Indirect (upstream)     | Same as Xray (Xray forked from v2ray)                                      | ~34,226 | Active               | ⭐⭐⭐⭐   |
| shadowsocks/shadowsocks-rust | [22]                                    | SS proxy (Rust)                       | Direct upstream         | `[[upstreams]] type = "shadowsocks"` in telemt config                      | 10,731  | Active               | ⭐⭐⭐⭐⭐ |
| database64128/shadowsocks-go | github.com/database64128/shadowsocks-go | SS proxy (Go)                         | Direct upstream         | Same as shadowsocks-rust (SS 2022)                                         | ~200    | Active               | ⭐⭐⭐⭐   |
| apernet/hysteria             | [23]                                    | QUIC-based proxy                      | Indirect (via sing-box) | sing-box as SOCKS5 upstream, sing-box exits via Hysteria2                  | 21,972  | Active               | ⭐⭐⭐⭐   |
| klzgrad/naiveproxy           | [24]                                    | Chromium-stack proxy                  | Indirect (upstream)     | SOCKS5 upstream; NaiveProxy exits via HTTPS with Chromium TLS              | 9,237   | Active               | ⭐⭐⭐⭐   |
| trojan-gfw/trojan            | github.com/trojan-gfw/trojan            | TLS-disguised proxy                   | Indirect (upstream)     | SOCKS5 upstream                                                            | 19,726  | Maintenance (2024)   | ⭐⭐⭐     |
| refraction-networking/utls   | github.com/refraction-networking/utls   | TLS fingerprint lib                   | Indirect (library)      | Used inside Xray/sing-box/mtg                                              | ~2,000  | Active               | ⭐⭐⭐⭐   |
| Danny-Dasilva/CycleTLS       | github.com/Danny-Dasilva/CycleTLS       | JA3/JA4 spoof (Go+JS)                 | Indirect (library)      | Used in custom Go upstream tools                                           | 1,478   | Active               | ⭐⭐⭐     |
| bogdanfinn/tls-client        | github.com/bogdanfinn/tls-client        | TLS fingerprint client                | Indirect (library)      | Custom Go tooling                                                          | 1,709   | Active               | ⭐⭐⭐     |
| ViRb3/wgcf                   | github.com/ViRb3/wgcf                   | Cloudflare WARP CLI                   | Indirect (upstream)     | Generate WireGuard profile → wireproxy exposes as SOCKS5 → telemt upstream | ~3,000  | Active               | ⭐⭐⭐⭐   |
| AmneziaVPN/amnezia-client    | github.com/amnezia-vpn/amnezia-client   | WireGuard obfuscation                 | Indirect                | Use as WireGuard upstream via wireproxy SOCKS5 bridge                      | ~5,000  | Active               | ⭐⭐⭐     |
| TUIC (sing-box built-in)     | —                                       | QUIC-based proxy                      | Indirect (via sing-box) | sing-box as SOCKS5 upstream with TUIC outbound                             | —       | Active (in sing-box) | ⭐⭐⭐     |

**Concrete upstream configuration examples for telemt `config.toml`:**

**Shadowsocks 2022 upstream:**

```toml
[general]
use_middle_proxy = false # required for SS upstream

[[upstreams]]
type = "shadowsocks"
url = "ss://2022-blake3-aes-256-gcm:BASE64KEY@127.0.0.1:8388"
weight = 10
enabled = true
```

**SOCKS5 upstream (Xray/sing-box/gost listening locally):**

```toml
[[upstreams]]
type = "socks5"
address = "127.0.0.1:1080"
weight = 10
enabled = true
```

**Load-balanced dual upstream:**

```toml
[[upstreams]]
type = "socks5"
address = "127.0.0.1:1080"
weight = 7
enabled = true

[[upstreams]]
type = "direct"
weight = 3
enabled = true
```

**Note on WARP upstream:** wgcf generates a WireGuard config from a Cloudflare WARP account. Use `wireproxy` (github.com/pufferffish/wireproxy) to expose the WireGuard tunnel as a SOCKS5 port, then point telemt at that SOCKS5 port. Direct WireGuard-to-SOCKS5 bridging without wireproxy requires additional tooling.

---

## Section 7 — Category F: Monitoring, Statistics, Alerts

| Project                                                  | URL                                     | Type                       | telemt integration            | ★       | Rating     |
| -------------------------------------------------------- | --------------------------------------- | -------------------------- | ----------------------------- | ------- | ---------- |
| Grafana Dashboard #25119 (Telemt Proxy Health)           | grafana.com/grafana/dashboards/25119    | Grafana dashboard          | Direct via Prometheus:9090    | —       | ⭐⭐⭐⭐⭐ |
| Grafana Dashboard #11904 (Telegram MTProto Proxy Status) | grafana.com/grafana/dashboards/11904    | Grafana dashboard          | mtg Prometheus endpoint       | —       | ⭐⭐⭐⭐   |
| Ty3uK/mtproto_proxy_exporter                             | github.com/Ty3uK/mtproto_proxy_exporter | Prometheus exporter        | Official MTProxy stats:8888   | ~50     | ⭐⭐⭐     |
| MTProxyMax Prometheus                                    | [6]                                     | Built-in exporter          | Direct (part of MTProxyMax)   | —       | ⭐⭐⭐⭐⭐ |
| mtproto.zig embedded dashboard                           | github.com/sleep3r/mtproto.zig          | Web dashboard + Prometheus | Direct (built into binary)    | ~1,100  | ⭐⭐⭐⭐   |
| Uptime Kuma                                              | github.com/louislam/uptime-kuma         | Uptime monitor             | TCP/HTTP check on telemt port | ~60,000 | ⭐⭐⭐⭐   |
| Loki + Promtail                                          | grafana.com/oss/loki                    | Log aggregation            | Scrape telemt systemd journal | —       | ⭐⭐⭐⭐   |
| Healthchecks.io (self-hosted)                            | github.com/healthchecks/healthchecks    | Cron/heartbeat monitor     | Ping from telemt cron job     | ~8,000  | ⭐⭐⭐     |

**Full monitoring stack for telemt (recommended):**

1. **telemt** exposes Prometheus metrics on `:9090` (configured in `config.toml`)
2. **Prometheus** scrapes `:9090` — standard scrape config, no exporter needed
3. **Grafana** imports dashboard ID `25119` — covers uptime, connections, traffic, upstream health, security events, per-user bandwidth
4. **Loki + Promtail** scrapes the telemt systemd journal for structured log analysis
5. **Uptime Kuma** adds external TCP/HTTP availability checks from a separate host
6. **MTProxyMax** adds Telegram-delivered alerts (quota exceeded, proxy down) via bot notifications

Grafana dashboard #25119 was last updated 2026-04-06 and requires Grafana 12.4.2+. For mtg-based deployments, use dashboard #11904 instead.

---

## Section 8 — Category G: Billing, Subscriptions, Paid Access

| Project                  | URL                                       | Type                          | MTProxy support               | Payment systems                                                | Automation                       | ★           | Rating           |
| ------------------------ | ----------------------------------------- | ----------------------------- | ----------------------------- | -------------------------------------------------------------- | -------------------------------- | ----------- | ---------------- |
| spyrae/ProxyCraft        | github.com/spyrae/proxycraft              | Full VPN/proxy Telegram shop  | Yes (via mtprotoproxy Docker) | Telegram Stars, YooKassa, YooMoney, T-Bank, Cryptomus, Heleket | Full (bot → payment → provision) | ~200        | ⭐⭐⭐⭐⭐       |
| SamNet-dev/MTProxyMax    | [6]                                       | Voucher billing layer         | Yes (native, telemt backend)  | Manual (voucher codes)                                         | Partial (voucher → access)       | ~620–2,500+ | ⭐⭐⭐⭐         |
| hiddify/Hiddify-Manager  | github.com/hiddify/Hiddify-Manager        | Multi-protocol panel          | Yes (with known iOS bugs)     | Via external bots                                              | Manual                           | ~15,000     | ⭐⭐⭐           |
| Gozargah/marzban         | github.com/gozargah/marzban               | VPN panel (Xray)              | **No** — Xray only            | Via marzban-shop bots                                          | N/A                              | ~8,000      | ⭐ (for MTProxy) |
| Marzneshin               | github.com/marzneshin/marzneshin          | VPN panel (Xray)              | **No**                        | Via external bots                                              | N/A                              | ~1,000      | ⭐ (for MTProxy) |
| 3x-ui / x-ui             | github.com/MHSanaei/3x-ui                 | VPN panel (Xray)              | **No**                        | Via 3xui-shop                                                  | N/A                              | ~15,000     | ⭐ (for MTProxy) |
| vpn-bot-stars-hiddify    | github.com/IgnatTOP/vpn-bot-stars-hiddify | Telegram bot shop for Hiddify | Via Hiddify                   | Telegram Stars                                                 | Yes                              | ~100        | ⭐⭐⭐           |
| CryptoPay / aiocryptopay | github.com/LulzLoL99/aiocryptopay         | Crypto payment library        | Via custom bot                | CryptoBot (@CryptoBot)                                         | Library only                     | ~200        | ⭐⭐⭐           |

**Critical finding:** Marzban, Marzneshin, and 3x-ui do **not** support MTProxy. They are Xray-core based. Do not invest integration effort with these panels for MTProxy.

**ProxyCraft limitation:** Uses `alexbers/mtprotoproxy` (Python) as backend, not telemt. For Russian operators needing FakeTLS, the proxy backend must be replaced with telemt, which requires custom integration work beyond ProxyCraft's current scope.

**Practical billing paths for telemt in 2026:**

1. **MTProxyMax vouchers + manual payment** — lowest effort, no payment gateway; operator sells voucher codes via any channel
2. **ProxyCraft bot + custom telemt backend** — requires replacing the proxy backend, but gives full payment automation with 6 gateways
3. **Custom aiogram/Telethon bot + telemt API** — full control; integrate CryptoPay or YooKassa directly; generate telemt secrets via REST API on payment confirmation

---

## Section 9 — Category H: Installation and Automation Scripts

| Project                            | URL                                           | Does                                                                                                                           | Server     | Quality   | Rating     |
| ---------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ---------- | --------- | ---------- |
| telemt install.sh                  | [4]                                           | Install/uninstall/update telemt; arch detect (x86_64/v3/aarch64), libc detect (glibc/musl), systemd/OpenRC, TLS config, ad_tag | telemt     | Excellent | ⭐⭐⭐⭐⭐ |
| MTProxyMax install                 | [6]                                           | Installs MTProxyMax + telemt engine; sets up bot, Prometheus, TUI                                                              | telemt     | Excellent | ⭐⭐⭐⭐⭐ |
| HirbodBehnam/MTProtoProxyInstaller | github.com/HirbodBehnam/MTProtoProxyInstaller | One-click install for official C proxy; firewall, systemd, dd/ee secrets                                                       | Official C | Good      | ⭐⭐⭐     |
| missuo/MTProxy                     | github.com/missuo/MTProxy                     | Bash installer claiming "v2"                                                                                                   | Official C | Basic     | ⭐⭐       |
| statix05/MTProxyInstall            | github.com/statix05/MTProxyInstall            | Docker-based install with watchdog                                                                                             | Official C | Basic     | ⭐⭐       |
| cimon-io/ansible-role-mtproxy      | github.com/cimon-io/ansible-role-mtproxy      | Ansible role, configurable version/repo                                                                                        | Official C | Good      | ⭐⭐⭐     |
| iShift/docker-compose-mtproxy      | github.com/iShift/docker-compose-mtproxy      | Docker Compose with watchdog                                                                                                   | Official C | Basic     | ⭐⭐       |
| Dofamin/MTProxy-Docker             | github.com/Dofamin/MTProxy-Docker             | Docker deployment for official proxy                                                                                           | Official C | Basic     | ⭐⭐       |
| yurykovshov/mtproto_proxy          | github.com/yurykovshov/mtproto_proxy          | Docker Compose for mtg                                                                                                         | mtg        | Basic     | ⭐⭐       |
| seriyps/mtproto_proxy installer    | github.com/seriyps/mtproto_proxy              | Interactive install for Ubuntu/Debian/CentOS                                                                                   | Erlang     | Good      | ⭐⭐⭐     |
| Medvedolog/telemt-openwrt          | github.com/Medvedolog/telemt-openwrt          | OpenWRT slim packages for telemt                                                                                               | telemt     | Good      | ⭐⭐⭐⭐   |
| web-elite/mtproto-proxy-installer  | github.com/web-elite/mtproto-proxy-installer  | Bash installer                                                                                                                 | Official C | Basic     | ⭐⭐       |

**Ansible/Terraform/Kubernetes/NixOS:** No production-ready Ansible role specifically for telemt was found (only for the official C proxy via cimon-io). No Terraform modules, NixOS modules, or Kubernetes manifests for telemt exist in the evidence. These are gaps — see Section 17.4.

**telemt install.sh customization:** The script accepts CLI arguments: `--domain`, `--port`, `--secret`, `--version`, `--lang` (en/ru), `--action` (install/uninstall/purge). This makes it scriptable for automated fleet deployment [5].

---

## Section 10 — Category I: Telegram DC Tools

| Project                               | URL                                     | Does                                                                                                                                      | telemt utility                                                     | Rating     |
| ------------------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------- |
| telemt/tools/dc.py                    | [14]                                    | Fetches live DC config via Telethon GetConfigRequest; OOP with DCServer dataclass; detects DC flags (IPv6, MEDIA-ONLY, CDN, TCPO, STATIC) | Diagnose DC reachability; identify optimal DC for upstream routing | ⭐⭐⭐⭐⭐ |
| MTProxyMax ping-dc / net-grade        | [6]                                     | TCP handshake latency to DC1–DC5; fastest-DC detection; A+/A/B/C quality grading                                                          | Choose optimal DC for upstream; diagnose connectivity              | ⭐⭐⭐⭐⭐ |
| fernvenue/telegram-cidr-list          | github.com/fernvenue/telegram-cidr-list | Daily-updated CIDR ranges for all Telegram IPs in multiple formats                                                                        | Firewall rules; routing policy for upstream                        | ⭐⭐⭐⭐   |
| MISP/misp-warninglists (telegram-ips) | [25]                                    | Telegram IP threat intelligence list                                                                                                      | Cross-reference blocked IPs; security monitoring                   | ⭐⭐       |
| gotd/td dcs package                   | [17]                                    | Go package with Telegram DC address constants                                                                                             | Build DC-aware Go tools                                            | ⭐⭐⭐     |
| ptc0219/TGDC                          | github.com/ptc0219/TGDC                 | Telegram DC status checker                                                                                                                | Verify DC availability from server                                 | ⭐⭐       |

**Telegram DC structure:** 5 independent datacenters (DC1–DC5). DC assignment is determined by phone number country at account registration time. MTProxy operators should route users to their home DC for lowest latency. `dc.py` uses `API_ID=123456` with Telethon to call `GetConfigRequest` and returns typed `DCServer` objects with all flags [14][26].

---

## Section 11 — Category J: Client Obfuscation (JA4 and TLS)

| Project                    | URL                                   | Does                                                                                                    | Platform      | How to use                                               | Status                   | Rating     |
| -------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------- | -------------------------------------------------------- | ------------------------ | ---------- |
| telemt/tdlib-obf           | [10]                                  | TDLib fork with 11 browser TLS profiles, DRS, IPT, ECH; activates only on ee-secret MTProxy connections | All (C++ lib) | Replace TDLib dep; build with `TDLIB_STEALTH_SHAPING=ON` | Active (2026-06-29)      | ⭐⭐⭐⭐⭐ |
| refraction-networking/utls | github.com/refraction-networking/utls | Go TLS library with browser fingerprint impersonation                                                   | Go apps       | Import in Go proxy tools; used inside Xray/sing-box      | Active                   | ⭐⭐⭐⭐   |
| Danny-Dasilva/CycleTLS     | github.com/Danny-Dasilva/CycleTLS     | JA3/JA4/HTTP2/QUIC fingerprint spoofing in Go+JS                                                        | Go, Node.js   | HTTP client library; not direct MTProxy integration      | Active (2026-06-12)      | ⭐⭐⭐     |
| bogdanfinn/tls-client      | github.com/bogdanfinn/tls-client      | net/http.Client with selectable TLS fingerprints                                                        | Go            | HTTP client library                                      | Active (2026-06-08)      | ⭐⭐⭐     |
| salesforce/ja3             | github.com/salesforce/ja3             | JA3/JA4 fingerprint computation (reference implementation)                                              | Python/Go     | Analyze fingerprints; verify obfuscation effectiveness   | Maintenance (2025-05-01) | ⭐⭐⭐     |
| ForkGram/ForkGram          | github.com/Forkgram/TelegramAndroid   | Telegram Android fork (privacy/UI)                                                                      | Android       | End-user client                                          | Active                   | ⭐⭐       |
| AyuGram/AyuGram            | github.com/AyuGram/AyuGram4A          | Telegram Android fork (privacy/UI)                                                                      | Android       | End-user client                                          | Active                   | ⭐⭐       |

**JA4 blocking context:** As of June 2026, telemt's own README explicitly states that Telegram client TLS ClientHello has been banned via JA4/JA4+ fingerprinting [1]. This means standard Telegram clients (official app, unmodified TDLib) can be blocked even when connecting through a telemt FakeTLS proxy — the DPI system identifies the client's fingerprint before the MTProxy layer matters. tdlib-obf solves this at the client level. ForkGram and AyuGram are privacy-focused forks but do **not** implement MTProto TLS obfuscation like tdlib-obf.

---

## Section 12 — Category K: Proxy Chains and Upstream Integrations

| Project                      | URL                                     | Type                                 | How to use with telemt                                             | ★      | Rating     |
| ---------------------------- | --------------------------------------- | ------------------------------------ | ------------------------------------------------------------------ | ------ | ---------- |
| shadowsocks/shadowsocks-rust | [22]                                    | SS 2022 server (Rust)                | `[[upstreams]] type = "shadowsocks" url = "ss://..."`              | 10,731 | ⭐⭐⭐⭐⭐ |
| database64128/shadowsocks-go | github.com/database64128/shadowsocks-go | SS 2022 server (Go)                  | Same as above                                                      | ~200   | ⭐⭐⭐⭐   |
| ginuerzh/gost                | github.com/ginuerzh/gost                | Multi-protocol tunnel (Go)           | SOCKS5 upstream; gost chains to any exit                           | 18,100 | ⭐⭐⭐⭐⭐ |
| 3proxy/3proxy                | github.com/3proxy/3proxy                | Multi-protocol proxy suite           | SOCKS5 upstream; supports chain building + random parent selection | ~4,000 | ⭐⭐⭐⭐   |
| ViRb3/wgcf + wireproxy       | github.com/ViRb3/wgcf                   | Cloudflare WARP → WireGuard → SOCKS5 | SOCKS5 upstream after wireproxy bridge                             | ~3,000 | ⭐⭐⭐⭐   |
| XTLS/Xray-core               | [13]                                    | VLESS/REALITY proxy                  | SOCKS5 upstream; Xray exits via REALITY                            | 40,013 | ⭐⭐⭐⭐⭐ |
| SagerNet/sing-box            | [16]                                    | Universal proxy platform             | SOCKS5 or SS upstream                                              | 35,579 | ⭐⭐⭐⭐⭐ |
| pufferffish/wireproxy        | github.com/pufferffish/wireproxy        | WireGuard → SOCKS5 bridge            | Bridges WARP WireGuard to SOCKS5 for telemt                        | ~3,000 | ⭐⭐⭐⭐   |
| alexbers/mtprotoproxy        | [18]                                    | Python MTProxy                       | Not an upstream; alternative server                                | ~1,000 | ⭐⭐       |
| microsocks                   | github.com/rofl0r/microsocks            | Minimal SOCKS5 server                | SOCKS5 upstream; minimal resource use                              | ~1,000 | ⭐⭐⭐     |

**Upstream compatibility note:** telemt's [[upstreams]] supports `direct`, `socks4`, `socks5`, and `shadowsocks` (ss-2022) natively [3]. VLESS, VMess, Trojan, and Hysteria2 are **not** directly supported — they require a bridge (SOCKS5 listener in Xray/sing-box) before telemt can use them. The `use_middle_proxy = false` constraint for Shadowsocks upstreams means ad_tag cannot be used simultaneously with SS upstream [3].

**Upstream config changes require process restart** — they are not hot-reloaded via the REST API [1].

---

## Section 13 — Category L: Secrets, Keys, Generators

| Project                            | URL                                           | Does                                                                                                               | Rating     |
| ---------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------- |
| Official MTProxy (built-in)        | [9]                                           | Generates 32-hex secrets via `head -c 16 /dev/urandom \| xxd -ps`; dd-prefix for DPI bypass; ee-prefix for FakeTLS | ⭐⭐⭐⭐   |
| mtg generate-secret                | [8]                                           | CLI: `mtg generate-secret --hex` or Base64; supports ee-prefix                                                     | ⭐⭐⭐⭐   |
| MTProxyMax secret commands         | [6]                                           | `mtproxymax secret add`, `mtproxymax secret qr`, `mtproxymax adtag set`; QR code generation                        | ⭐⭐⭐⭐⭐ |
| mtbuddy (mtproto.zig)              | github.com/sleep3r/mtproto.zig                | `mtbuddy secret` generates ee-prefixed secrets                                                                     | ⭐⭐⭐     |
| seriyps/mtproto_proxy              | github.com/seriyps/mtproto_proxy              | Supports dd-prefix (34 chars) and ee/base64 for FakeTLS; multiple secrets per port                                 | ⭐⭐⭐⭐   |
| HirbodBehnam/MTProtoProxyInstaller | github.com/HirbodBehnam/MTProtoProxyInstaller | Auto-generates dd-prefix and ee-prefix secrets during install                                                      | ⭐⭐⭐     |
| dev-ir/Telegram-MTProto-Proxy      | github.com/dev-ir/Telegram-MTProto-Proxy      | Web tool: generates + parses tg://proxy and https://t.me/proxy links for all protocols                             | ⭐⭐⭐⭐   |
| SMTech-List/mtproto_tool           | github.com/SMTech-List/mtproto_tool           | GUI/CLI with QR code generation (uses `qrcode` library)                                                            | ⭐⭐⭐     |
| teleproxy deploy page              | [19]                                          | Web deploy page generates unique secret + QR code                                                                  | ⭐⭐⭐     |

**Secret format reference:**

- **Plain hex (32 chars):** `0123456789abcdef0123456789abcdef` — Classic mode, no DPI protection
- **dd-prefix (34 chars):** `dd0123456789abcdef0123456789abcdef` — adds random padding to each packet, defeats statistical DPI
- **ee-prefix:** `ee` + base64(domain) — FakeTLS mode; the domain is the SNI target for TLS masking

**tg://proxy link schema:** `tg://proxy?server=HOST&port=PORT&secret=SECRET` [9]. HTTPS variant: `https://t.me/proxy?server=HOST&port=PORT&secret=SECRET`. Both formats are functionally equivalent; Telegram clients accept either.

---

## Section 14 — Category M: Awesome Lists and Documentation

| Resource                            | URL                                              | Contains                                                                                    | Currency         | Rating     |
| ----------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------- | ---------------- | ---------- |
| danoctavian/awesome-anti-censorship | github.com/danoctavian/awesome-anti-censorship   | Network tunnels section includes MTProxy; curates DPI bypass tools                          | Maintained       | ⭐⭐⭐⭐   |
| serhii-londar/awesome-telegram      | github.com/serhii-londar/awesome-telegram        | MTProto implementations section: Kotlogram, MadelineProto, telegram-cli, gramme.rs          | Maintained       | ⭐⭐⭐⭐   |
| marzneshin/awesome-anticensor       | github.com/marzneshin/awesome-anticensor         | Censorship circumvention cores: Xray, sing-box, Hysteria, WireGuard; GUI clients; resources | Updated Oct 2024 | ⭐⭐⭐     |
| awesome-selfhosted                  | github.com/awesome-selfhosted/awesome-selfhosted | Proxy section; MTProxy not prominently featured                                             | Maintained       | ⭐⭐       |
| GitHub topic: mtproto-proxy         | [27]                                             | 91 repositories; primary discovery point for all MTProxy implementations                    | Live             | ⭐⭐⭐⭐⭐ |
| GitHub topic: mtproto               | github.com/topics/mtproto                        | 480+ repositories across all MTProto-related projects                                       | Live             | ⭐⭐⭐⭐⭐ |
| telemt FAQ.en.md                    | [3]                                              | Upstream config, DC assignment, secret formats, Shadowsocks constraints                     | Current (2026)   | ⭐⭐⭐⭐⭐ |
| tdlib-obf Integration Guide         | [11]                                             | Full integration guide for custom client builds with tdlib-obf                              | Current (2026)   | ⭐⭐⭐⭐⭐ |

---

## Section 15 — Category N: telemt Forks

telemt has 246 forks [28]. Most are simple mirrors or packaging variants. Significant forks with code changes:

| Owner/Fork                       | URL                                  | What changed                                                                     | Why                              | Worth attention?                               |
| -------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------- | -------------------------------- | ---------------------------------------------- |
| Medvedolog/telemt-openwrt        | github.com/Medvedolog/telemt-openwrt | OpenWRT packaging; slim binary build                                             | Deploy telemt on router hardware | Yes — only maintained OpenWRT packaging        |
| afadillo-a11y/telemt_wrt         | github.com/afadillo-a11y/telemt_wrt  | OpenWRT build system adaptations                                                 | Router deployment                | Yes — active, forked from Medvedolog           |
| kozhini/telemt_wrt               | github.com/kozhini/telemt_wrt        | 15 commits ahead of afadillo-a11y; adds ad-tag support configuration             | Ad-tag on OpenWRT                | Yes — most feature-complete OpenWRT fork       |
| evl38784 (fork of afadillo-a11y) | (requires verification)              | Further OpenWRT packaging adaptations                                            | Embedded deployment              | Moderate                                       |
| unuunn/telemt-ssu                | github.com/unuunn/telemt-ssu         | Selective Socks Upstream (SSU): route specific users through different upstreams | Per-user upstream routing        | Yes — unique feature not in main telemt        |
| deknowny (fork)                  | (requires verification)              | Dynamic upstream mesh reload without process restart                             | Hot upstream config reload       | Yes — closes a known limitation of main telemt |
| StealthSurf-VPN/telemt           | github.com/StealthSurf-VPN/telemt    | Additional stealth presets                                                       | Commercial deployment            | Moderate                                       |
| amirotin/telemt                  | github.com/amirotin/telemt           | Minor config changes                                                             | Personal deployment              | No                                             |
| 13werwolf13/telemt               | github.com/13werwolf13/telemt        | Minor changes                                                                    | Personal deployment              | No                                             |

**Key gap in main telemt filled by forks:** Selective per-user upstream routing (unuunn/telemt-ssu) — in main telemt, all users share the same upstream pool. If you need to route premium users through WARP and free users direct, this fork is the only available solution.

---

## Section 16 — Category O: Miscellaneous and Unexpected

| Project                           | URL                                          | Category                 | Description                                                                | Rating |
| --------------------------------- | -------------------------------------------- | ------------------------ | -------------------------------------------------------------------------- | ------ |
| SoliSpirit/mtproto                | github.com/SoliSpirit/mtproto                | Public proxy list        | Auto-updated every 12 hours with verified MTProto proxies                  | ⭐⭐⭐ |
| Grim1313/mtproto-for-telegram     | github.com/Grim1313/mtproto-for-telegram     | Public proxy list        | Free MTProto proxies, 12-hour update cycle                                 | ⭐⭐⭐ |
| MT-proxy-bot-SG                   | github.com/thejan64go/MT-proxy-bot-SG        | Proxy aggregator bot     | 300+ proxies from 18+ countries, smart selection by country/DC/performance | ⭐⭐   |
| p1ratrulezzz/mtproxy-server-linux | github.com/p1ratrulezzz/mtproxy-server-linux | Linux setup scripts      | Useful scripts for MTProxy setup on Linux                                  | ⭐⭐   |
| mini-telegram                     | github.com/topics/mtproto-server             | Telegram server emulator | Unofficial monolithic MTProto server in Rust; not production-ready         | ⭐     |
| A Node.js CLI proxy verifier      | github.com/topics/mtproxy?l=javascript       | Proxy checker            | Verifies MTProxy connectivity using TDLib API                              | ⭐⭐   |
| 3140/MTProxy                      | github.com/3140/MTProxy                      | Zero-config Docker       | Docker container for official MTProxy with zero configuration              | ⭐⭐   |
| mtproto_proxy_exporter (Ty3uK)    | github.com/Ty3uK/mtproto_proxy_exporter      | Prometheus exporter      | Exports official MTProxy stats to Prometheus                               | ⭐⭐⭐ |
| alexdoesh/mtproxy                 | github.com/alexdoesh/mtproxy                 | Multi-secret C fork      | Fork of official MTProxy supporting up to 16 secrets with auto-generation  | ⭐⭐   |
| mmdzov/mtproxybot                 | github.com/mmdzov/mtproxybot                 | Basic management bot     | JS bot, /start and /reset only, 2 stars, inactive since Jan 2024           | ⭐     |

---

## Section 17 — Final Summary

### 17.1 Top-10 Projects for Immediate Use

| Project                           | Category               | Why needed right now                                                                                       | Rating     |
| --------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------- | ---------- |
| telemt/telemt [1]                 | A (Server)             | The only production-ready server for Russia 2026: FakeTLS, ad_tag, upstream chaining, Prometheus           | ⭐⭐⭐⭐⭐ |
| SamNet-dev/MTProxyMax [6]         | B (Panel)              | Multi-user management, 21-command bot, voucher billing, Prometheus — wraps telemt with everything it lacks | ⭐⭐⭐⭐⭐ |
| telemt/tdlib-obf [10]             | J (Client obfuscation) | JA4 fingerprint bypass — without this, FakeTLS alone is insufficient as of June 2026                       | ⭐⭐⭐⭐⭐ |
| Grafana Dashboard #25119          | F (Monitoring)         | Purpose-built telemt dashboard; import ID 25119 into Grafana, point at:9090                                | ⭐⭐⭐⭐⭐ |
| telemt install.sh [4]             | H (Automation)         | Multi-arch installer with ad_tag, TLS config, systemd/OpenRC — one command to production                   | ⭐⭐⭐⭐⭐ |
| shadowsocks/shadowsocks-rust [22] | K (Upstream)           | Direct SS 2022 upstream support in telemt config.toml; adds encrypted upstream layer                       | ⭐⭐⭐⭐⭐ |
| XTLS/Xray-core [13]               | E (DPI bypass)         | REALITY upstream via SOCKS5 bridge; strongest available DPI bypass for telemt chains                       | ⭐⭐⭐⭐⭐ |
| LonamiWebs/Telethon [12]          | D (Library)            | Used in telemt's own tooling; build management bots and DC diagnostics in Python                           | ⭐⭐⭐⭐   |
| spyrae/ProxyCraft                 | G (Billing)            | Only off-the-shelf solution with 6 payment gateways including Russian (YooKassa, T-Bank)                   | ⭐⭐⭐⭐   |
| 9seconds/mtg [8]                  | A (Server)             | Go alternative for resource-constrained servers; no ad_tag in v2 but solid FakeTLS                         | ⭐⭐⭐⭐   |

### 17.2 Top-5 Projects to Watch

1. **unuunn/telemt-ssu** — Selective per-user upstream routing (not in main telemt). Will become critical once operators need to tier users by upstream quality.
2. **sleep3r/mtproto.zig** — VLESS/REALITY native upstream without SOCKS5 bridge; 177KB binary. Zig ecosystem maturity is the only blocker.
3. **danielVNru/mtproto-panel** — Full-stack React+Express+PostgreSQL panel with multi-node orchestration. Needs more community adoption and testing.
4. **deknowny fork of telemt** — Dynamic upstream mesh reload without restart. If merged upstream, eliminates a key operational pain point.
5. **Hiddify-Manager** — The only major multi-protocol panel with MTProxy support. iOS compatibility bugs (issue #4623) are the current blocker for production use.

### 17.3 Top-5 Ideas to Build Yourself

1. **Payment-to-telemt-secret bridge:** A Telegram bot that accepts CryptoPay/YooKassa payment webhooks and calls telemt's REST API (`POST /v1/users`) to provision a new secret, then sends the `tg://proxy` link with QR code to the user. MTProxyMax has the voucher side; this closes the payment-gateway side. Estimated scope: ~500 lines of Python with aiogram + aiocryptopay.

2. **Ansible role for telemt fleet:** The existing `cimon-io/ansible-role-mtproxy` targets the official C proxy. A role for telemt would: run `install.sh` with CLI args, template `config.toml` from inventory variables, configure Prometheus scraping, and handle upstream pool updates. No such role exists yet.

3. **Per-user upstream routing UI:** Expose `unuunn/telemt-ssu`'s selective upstream feature through MTProxyMax's bot interface — add `/mp_upstream_user <user> <upstream>` command. Currently there is no UI for this feature.

4. **telemt Kubernetes manifest + Helm chart:** No Helm chart or K8s manifest exists for telemt. A chart with: Deployment (telemt container), Service (NodePort/LoadBalancer), ConfigMap (config.toml), Secret (ad_tag, upstream credentials), and ServiceMonitor (Prometheus Operator) would enable cloud-native fleet management.

5. **JA4 fingerprint rotation scheduler:** A cron job that periodically rotates the active browser profile in tdlib-obf (if the library exposes this at runtime) or triggers client updates when a profile is detected as blocked. Currently tdlib-obf selects a profile at build time.

### 17.4 Ecosystem Gaps

- **No Terraform/Pulumi module for telemt** — cloud infrastructure provisioning must be scripted manually.
- **No NixOS module for telemt** — NixOS users cannot install telemt declaratively.
- **No Kubernetes-native deployment** — no Helm chart, no Operator, no ServiceMonitor for Prometheus Operator.
- **No direct payment gateway in MTProxyMax** — vouchers require manual distribution; the payment-to-provision flow must be built separately.
- **No pre-built tdlib-obf APK or desktop client** — operators cannot distribute obfuscated clients to end users without building from source.
- **No unified multi-server dashboard** — MTProxyMax manages one telemt instance per installation; managing a fleet of 10+ servers requires either mtproto-panel (still maturing) or custom tooling.
- **No automated JA4 fingerprint monitoring** — no tool alerts operators when a specific browser profile in tdlib-obf is being detected/blocked.

### 17.5 Architectural Recommendation

```
[Telegram Client with tdlib-obf] ← replaces standard TDLib
 ↓ TLS 1.3 (browser fingerprint)
[telemt/telemt] — FakeTLS/ee mode, port 443
 github.com/telemt/telemt [1]
 ↓ [[upstreams]] in config.toml
[Upstream layer — choose one or weighted mix]
 ├── shadowsocks-rust (ss-2022, local SOCKS5) [22]
 ├── Xray-core REALITY (local SOCKS5 listener) [13]
 ├── sing-box TUIC/Hysteria2 (local SOCKS5) [16]
 └── wgcf + wireproxy → Cloudflare WARP (SOCKS5)
 ↓
[Telegram DC1–DC5]
 ↑ management plane
[SamNet-dev/MTProxyMax] — wraps telemt engine [6]
 ├── Telegram bot (21 commands, user CRUD, QR links)
 ├── Voucher billing (MTP-XXXX codes)
 └── Prometheus metrics:9090
 ↓
[Prometheus → Grafana Dashboard #25119]
 — connections, traffic, upstream health, per-user BW
 ↓
[Loki + Promtail] — log aggregation from systemd journal
 ↓
[Billing layer — build or adapt]
 ├── Option A: MTProxyMax vouchers + manual payment channel
 ├── Option B: ProxyCraft bot (replace proxy backend with telemt)
 └── Option C: Custom aiogram bot + telemt REST API + aiocryptopay/YooKassa
 ↓
[DC diagnostics]
 ├── telemt/tools/dc.py [14] — live DC config via Telethon
 └── MTProxyMax ping-dc / net-grade [6] — latency benchmarking
```

**Minimum viable production stack (3 components):**

1. `telemt` with FakeTLS + ad_tag configured
2. `MTProxyMax` for user management and monitoring
3. Grafana dashboard #25119 for observability

**Full production stack (add for scale):** 4. `shadowsocks-rust` or `Xray-core` as upstream for DPI resistance depth 5. `tdlib-obf`-based client build for JA4 bypass 6. Custom payment bot (aiogram + CryptoPay) for monetization automation

---

## Section 18 — Directions for Further Research

**1. telemt fork analysis: what patches are being applied**
Walk the 246 forks [28], identify those with commits ahead of main, diff against the canonical branch. Specifically: what security patches has `kozhini/telemt_wrt` applied beyond ad-tag config? What does `deknowny`'s dynamic upstream reload change in the connection lifecycle? What does `unuunn/telemt-ssu`'s selective upstream add to the routing table? This would reveal whether any forks have closed security issues that the main repo has not yet merged.

**2. Billing comparison: ProxyCraft vs MTProxyMax vouchers vs custom bot**
Structured comparison across three dimensions: (a) time-to-first-paid-user (setup complexity), (b) supported payment gateways and their Russia availability in 2026 (Telegram Stars, T-Bank, CryptoPay), (c) automation depth (payment → secret provisioning → renewal notification without operator intervention). ProxyCraft uses mtprotoproxy as backend — quantify the effort to replace it with telemt.

**3. JA4 blocking timeline and tdlib-obf effectiveness**
The telemt README states JA4/JA4+ fingerprint banning was active as of June 2026. Research questions: which DPI system (TSPU, Roskomnadzor infrastructure, ISP-level) is performing the fingerprint matching? Which of tdlib-obf's 11 browser profiles are currently undetected? How quickly do new profiles become fingerprinted after tdlib-obf releases them? This would determine the operational shelf-life of each profile and inform how frequently operators need to push client updates.

## References

[1] telemt/telemt - GitHub. https://github.com/telemt/telemt
[2] telemt/config.toml at main. https://github.com/telemt/telemt/blob/main/config.toml
[3] telemt/docs/FAQ.en.md at main - GitHub. https://github.com/telemt/telemt/blob/main/docs/FAQ.en.md
[4] telemt/install.sh - GitHub. https://github.com/telemt/telemt/blob/main/install.sh
[5] telemt install.sh - Raw GitHub Content. https://raw.githubusercontent.com/telemt/telemt/main/install.sh
[6] SamNet-dev/MTProxyMax - GitHub. https://github.com/SamNet-dev/MTProxyMax
[7] MTProxyMax - GitHub. https://github.com/SamNet-dev/MTProxyMax/blob/main/README.md
[8] 9seconds/mtg - GitHub. https://github.com/9seconds/mtg
[9] TelegramMessenger/MTProxy - GitHub. https://github.com/TelegramMessenger/MTProxy
[10] telemt/tdlib-obf - GitHub. https://github.com/telemt/tdlib-obf
[11] Full Integration Guide for tdlib-obf. https://github.com/telemt/tdlib-obf/blob/master/docs/Documentation/CUSTOM_CLIENT_INTEGRATION_GUIDE.md
[12] lonamiwebs/telethon - GitHub. https://github.com/lonamiwebs/telethon
[13] XTLS/Xray-core - GitHub. https://github.com/XTLS/Xray-core
[14] telemt/tools/dc.py - GitHub. https://github.com/telemt/telemt/blob/main/tools/dc.py
[15] tdlib/td - GitHub. https://github.com/tdlib/td
[16] SagerNet/sing-box - GitHub. https://github.com/SagerNet/sing-box
[17] gotd/td - Telegram MTProto API client in Go. https://github.com/gotd/td
[18] alexbers/mtprotoproxy - GitHub. https://github.com/alexbers/mtprotoproxy
[19] teleproxy/teleproxy. https://github.com/teleproxy/teleproxy
[20] Scratch-net/telego. https://github.com/scratch-net/telego
[21] danielVNru/mtproto-panel - GitHub. https://github.com/danielVNru/mtproto-panel
[22] shadowsocks/shadowsocks-rust. https://github.com/shadowsocks/shadowsocks-rust
[23] Hysteria is a powerful, lightning fast and censorship .... https://github.com/apernet/hysteria
[24] klzgrad/naiveproxy: Make a fortune quietly. https://github.com/klzgrad/naiveproxy
[25] MISP warninglists - GitHub. https://github.com/MISP/misp-warninglists/blob/main/lists/telegram-ips/list.json
[26] telemt - tools/dc.py source. https://git.stelm.me/astelm/telemt/src/commit/a5c7a41c49490ddb87fbd723aef17682bea9c79a/tools/dc.py
[27] mtproto-proxy · GitHub Topics. https://github.com/topics/mtproto-proxy
[28] Fork network members - telemt/telemt. https://github.com/telemt/telemt/network/members
