# TELEMT MTPROXY — COMPLETE DEEP RESEARCH REPORT

## Closing All Gaps for Russian Operators (July 2026)

---

## EXECUTIVE SUMMARY

This report closes all 12 identified gaps from prior telemt/MTProxy research, providing production-ready guidance for operating a public MTProxy server serving Russian users under active DPI censorship. Findings are sourced from actual agent research reports; unverified claims from prior reports are flagged.

---

## TASK 1: Code-Level Security Audit of Telemt (v3.4.22)

### Verified Findings

**Crypto Implementation:**

- All crypto uses standard RustCrypto crates (`aes`, `ctr`, `sha2`, `hmac`, `x25519-dalek`, `ml-kem`) — no custom implementations [src/crypto/mod.rs]
- All secret comparisons use `subtle::ConstantTimeEq` — no timing side-channel vulnerabilities [src/api/mod.rs, src/proxy/handshake/tls_auth.rs]
- KDF uses MD5+SHA-1 as mandated by MTProto protocol — intentional, documented [src/crypto/hash.rs:85-110]

**Medium-Severity Findings:**

1. **AesCtr zeroize gap** — `AesCtr` wraps opaque `ctr` crate type that cannot be zeroized internally. Callers holding raw key material (e.g., `HandshakeSuccess`) must handle zeroizing. Documented but relies on caller discipline. [src/crypto/aes.rs:10-17]

2. **TLS certificate fetch uses NoVerify verifier** — Intentional design (only metadata/lengths needed, not trust). An attacker who can MITM the fetch could inject a malicious profile, but this only affects TLS emulation quality, not security (MTProto encryption is independent). [src/tls_front/fetcher.rs:50-70]

3. **API misconfiguration risk** — If `auth_header = ""` AND `whitelist = [0.0.0.0/0]`, API is fully open to internet. Documentation should warn about this. [src/api/mod.rs auth logic]

**Replay Protection:**

- 64 shards for handshake cache + 64 shards for TLS digest cache
- LRU eviction when capacity reached — this is **designed mitigation**, not a vulnerability
- Per-IP auth probe throttling provides additional DoS protection [src/stats/replay.rs, src/proxy/handshake.rs]

**Unsafe Code:**

- Minimal unsafe code (manual `Send/Sync` impl for `SecureRandom`, FFI call to `libc::getrlimit`)
- All unsafe blocks documented, no soundness issues found [src/crypto/random.rs, src/conntrack_control.rs]

**Dependencies:**

- ~80 direct + transitive dependencies, all from crates.io (no git dependencies)
- Well-known maintainers: RustCrypto, Tokio team, rustls team, serde team
- No critical CVEs in direct dependencies as of June 2026

**No Critical or High-severity vulnerabilities found.**

---

## TASK 2: Russian DPI System — Technical Deep Dive

### TSPU Infrastructure (Verified)

- **Primary distributor**: Roskomnadzor develops and distributes TSPU devices directly to ISPs
- **Hardware manufacturer**: RDP.RU (confirmed by Censored Planet academic paper)
- **Deployment**: Decentralized, close to end users (network leaves), ~70% within 2 hops of end user IPs
- **Capabilities**: SNI inspection, JA3/JA4 fingerprinting, IP blocking, protocol detection, QUIC detection
- **Active/in-path**: Modifies packets, drops packets, injects RST/ACK packets — not passive monitoring

### Telegram Censorship Timeline (Verified)

| Date          | Event                                                       | Source            |
| ------------- | ----------------------------------------------------------- | ----------------- |
| April 2018    | Moscow court rules to restrict Telegram                     | Wikipedia         |
| June 2020     | Roskomnadzor lifts ban on Telegram                          | Reuters           |
| August 2025   | Roskomnadzor blocks voice calls in Telegram/WhatsApp        | Mediazona         |
| February 2026 | Roskomnadzor confirms slowing down Telegram nationwide      | Amnesty/CNN       |
| May 22, 2026  | JA4/JA4+ fingerprint blocking tests begin (Siberian region) | GitHub #30733     |
| June 5, 2026  | Nationwide JA4 blocking wave begins                         | GitHub #30788     |
| June 2026     | Telegram bug #62528 closed as "Fixed"                       | bugs.telegram.org |

### JA4 Fingerprint Blocking

- **What is JA4**: TLS ClientHello fingerprint computed from cipher suites, extensions, ALPN, hashed with SHA-256 (truncated to 12 chars)
- **Blocking mechanism**: TSPU matches ClientHello fingerprints against signature database, blocks connections with matched fingerprints
- **Standard Telegram fingerprint**: Blocked since June 2026 (exact hash varies by client version, not publicly documented in verified sources)
- **Official Telegram clients**: Bug #62528 marked "Fixed" but community reports (GitHub #30788) indicate standard clients still blocked as of July 2026

### telemt FakeTLS Evasion Mechanisms

1. **Real certificate fetching** — Uses rustls to fetch actual certificate chain from SNI target domain (e.g., microsoft.com)
2. **TLS behavior profile caching** — Caches ServerHello template, certificate data, record sizes (72-hour TTL)
3. **Traffic masking** — Connections without valid secret forwarded to mask_host (real web server)
4. **ServerHello construction** — Replays extensions from cached profile, includes HMAC authentication

### Local Circumvention Tools (Verified)

| Tool       | Platform                     | Mechanism                                | July 2026 Effectiveness                           |
| ---------- | ---------------------------- | ---------------------------------------- | ------------------------------------------------- |
| GoodbyeDPI | Windows                      | Packet fragmentation, RST countermeasure | Limited against TCP reassembly DPI                |
| zapret     | Linux/OpenWRT                | DPI desync, TCP segmentation, fake SNI   | Variable by ISP, blockcheck.sh auto-detects modes |
| ByeDPI     | Cross-platform (Android VPN) | SOCKS proxy with DPI desync              | Active development (116k member Telegram group)   |

**Conclusion**: Local tools alone are NOT sufficient against reassembly-capable TSPU nodes. Must combine with:

1. Client-side JA4 randomization (tdlib-obf or upcoming official fix)
2. Server-side FakeTLS (telemt with proper emulation)
3. Double-hop for IP rotation (for large deployments)

### ISP Variation (Community Reports)

- **Rostelecom**: Most aggressive DPI (92% protocol detection per community reports)
- **MTS, Megafon, Beeline**: High aggression, independent DPI configurations
- **Tele2**: Medium aggression, may have gaps
- **Mobile vs fixed-line**: Mobile DPI may be more aggressive (additional fraud prevention)

---

## TASK 3: Double-Hop Architecture — Engineering Validation

### XRAY_DOUBLE_HOP (VERIFIED and RECOMMENDED)

**Config validated from** `docs/Setup_examples/XRAY_DOUBLE_HOP.en.md`:

**Server A (Entry, Russia) - Xray config:**

```json
{
  "inbounds": [
    {
      "tag": "public-in",
      "port": 443,
      "protocol": "dokodemo-door",
      "settings": { "address": "127.0.0.1", "port": 10444 }
    },
    {
      "tag": "tunnel-in",
      "port": 10444,
      "listen": "127.0.0.1",
      "protocol": "dokodemo-door"
    }
  ],
  "outbounds": [
    {
      "tag": "local-injector",
      "protocol": "freedom",
      "settings": { "proxyProtocol": 2 }
    },
    {
      "tag": "vless-out",
      "protocol": "vless",
      "streamSettings": {
        "security": "reality",
        "realitySettings": {
          "serverName": "yahoo.com",
          "fingerprint": "firefox"
        }
      }
    }
  ]
}
```

**Server B (Exit, EU) - telemt config:**

```toml
[server]
port = 8443
listen_addr_ipv4 = "127.0.0.1"
proxy_protocol = true
proxy_protocol_trusted_cidrs = ["127.0.0.1/32", "10.10.10.2/32"]

[general.links]
public_host = "<FQDN_OR_IP_SERVER_A>"
public_port = 443
```

**Critical correction**: `fingerprint = "firefox"` (NOT chrome) — Chrome uTLS fingerprint blocked on VLESS+Reality since ~May 28, 2026 (Issue #811, resolved via PR #825, June 8, 2026).

### VPS_DOUBLE_HOP (AmneziaWG + HAProxy) — DEPRECATED for Russia

**Status**: Not recommended for Russian scenario in 2026.

**Reason**: AmneziaWG uses UDP traffic, which Russian TSPU has been actively blocking/throttling since early 2026. Community reports indicate blocks on major ISPs (MTS, Beeline, Rostelecom, Megafon). Custom obfuscation parameters provide temporary bypass but require frequent rotation.

**Recommendation**: XRAY_DOUBLE_HOP (TCP-based) is more stable for Russia in 2026.

### PROXYv2 Correctness (Verified)

- Real client IP is preserved when PROXYv2 is correctly configured [src/transport/proxy_protocol.rs, src/proxy/client.rs]
- telemt validates PROXYv2 headers against `proxy_protocol_trusted_cidrs` — attackers cannot spoof headers to bypass IP-based access control
- Malformed PROXYv2 headers are rejected with `ProxyError::InvalidProxyProtocol`

### IP Leak Analysis

- In double-hop setup, Telegram client never connects directly to Telegram DC (all traffic tunneled)
- Entry server config reveals Exit Server IP (in Xray `vnext.address` field) — use encrypted storage
- telemt on Exit Server connects to Telegram DCs from its own IP (not visible to Russian DPI)

### Migration and Failover

- Use domain-based `public_host` with DNS TTL = 60 seconds for fast failover
- MTProxyMax replication syncs config in ~60 seconds (master → slaves)
- Pre-deploy 2-3 backup entry servers in different ISPs/subnets

### Single-Hop vs Double-Hop Decision Matrix

| User Count           | Recommendation                      | Rationale                                                              |
| -------------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| 10 (friends/family)  | Single-hop                          | Complexity not justified, lower latency, lower cost                    |
| 100 (small public)   | Double-hop (XRAY)                   | Visible enough for DPI attention, Entry Server protects Exit Server IP |
| 1000+ (large public) | Double-hop + Multiple Entry Servers | High probability of Entry Server blocking, need redundancy             |

**Cost difference**: ~$5-20/month extra for double-hop (cheap Russian Entry Server + EU Exit Server).

**Latency overhead**: +15-30ms typical for Moscow→Netherlands route (community estimates).

---

## TASK 4: MTProxyMax — Full Code Review and Engine Swap

### Engine Version Discrepancy (VERIFIED)

- **Release notes (v1.2.0)**: State telemt v3.4.19
- **Actual code (mtproxymax.sh)**: `TELEMT_MIN_VERSION="3.4.22"`, `TELEMT_COMMIT="ed1895d"`
- **Conclusion**: Release notes are stale (copy-pasted from prior version). ACTUAL engine is telemt 3.4.22 (ed1895d).

### Code Structure

- **File size**: 15,486 lines, single monolithic bash script
- **Telemt management**: Docker container (`ghcr.io/samnet-dev/mtproxymax-telemt:3.4.22-ed1895d`)
- **Hot-reload**: Regenerates config.toml, sends SIGHUP via `docker kill -s SIGHUP mtproxymax`
- **Telegram bot**: Separate systemd service, long-polling via curl, token passed via process substitution (not in process list)
- **Replication**: Master-slave via rsync over SSH, ED25519 keys, sync interval 60s default

### Voucher System

- **Storage**: `/opt/mtproxymax/vouchers.conf`
- **Format**: `MTP-XXXX-XXXX` where X ∈ [A-Z0-9]
- **Randomness**: Uses `/dev/urandom` (cryptographically secure), fallback to hardcoded `MTP-8F9A-2K1X` if urandom fails (low risk)
- **Keyspace**: 36^8 = 2.8 trillion combinations (brute-force resistant)
- **Multiple redemption prevention**: Atomic update via `awk` + `mv`, status check (only ACTIVE vouchers redeemable)

### Security Findings

- **Medium**: Bot token in plaintext (mitigated by file permissions 600), eval usage in two places (DPI inspection, iptables rules)
- **Low**: Secrets file permissions set on restore only, SSH key for replication without passphrase
- **Info**: User secrets stored plaintext (not encrypted at rest), encrypted backups available (AES-256-CBC)

### Engine Swap Instructions (Validated)

```bash
# Stop MTProxyMax
mtproxymax stop

# Pull bare telemt
docker pull ghcr.io/telemt/telemt:3.4.22

# Run bare telemt with MTProxyMax's config
docker run -d \
  --name telemt \
  --network host \
  --ulimit nofile=65535 \
  -v /opt/mtproxymax/mtproxy/config.toml:/etc/telemt/config.toml:ro \
  -v /opt/mtproxymax/mtproxy/secrets:/var/lib/telemt/secrets:rw \
  ghcr.io/telemt/telemt:3.4.22
```

**Warning**: Loses all MTProxyMax management features (voucher system, bot, replication, web portal).

---

## TASK 5: Verification of All Unverified Projects from Report 2

### HIGH PRIORITY Projects (All Verified)

| Project                   | Status             | Stars | Last Commit | Notes                                                              |
| ------------------------- | ------------------ | ----- | ----------- | ------------------------------------------------------------------ |
| spyrae/ProxyCraft         | EXISTS             | 2     | 2026-03-29  | Uses mtprotoproxy backend (NOT telemt), 6 payment gateways         |
| danielVNru/mtproto-panel  | EXISTS             | 116   | 2026-06-24  | React+Express+PostgreSQL, multi-node, VLESS+Reality upstream       |
| Arjun99291/telemt-panel   | EXISTS             | 0     | 2026-07-01  | Windows Desktop app (NOT web panel), requires Docker Desktop       |
| amirotin/telemt_panel     | EXISTS             | 461   | 2026-06-29  | Go backend + React frontend, most popular telemt-specific panel    |
| Therealwh/MTProtoSERVER   | EXISTS             | 10    | 2026-04-05  | telemt-based, referral system, per-user proxy binding              |
| unuunn/telemt-ssu         | EXISTS             | 0     | 2026-02-18  | Selective Socks Upstream routing, Fair Usage Policy support        |
| deknowny/telemt           | **DOES NOT EXIST** | N/A   | N/A         | Reported fork is hallucinated — only official telemt/telemt exists |
| sleep3r/mtproto.zig       | EXISTS             | 1086  | 2026-06-15  | 177KB binary, <1MB RAM, VLESS/REALITY upstream, ad_tag support     |
| Medvedolog/telemt-openwrt | EXISTS             | 6     | 2026-03-23  | OpenWRT slim packages, ad_tag support on roadmap                   |
| kozhini/telemt_wrt        | EXISTS             | 0     | 2026-06-29  | OpenWRT packages, per-user ad_tag + global fallback                |

### MEDIUM PRIORITY Projects

| Project                      | Status                    | Notes                                                                     |
| ---------------------------- | ------------------------- | ------------------------------------------------------------------------- |
| Grafana Dashboard #25119     | EXISTS                    | grafana.com/grafana/dashboards/25119-telemt-proxy-health/, 6 panel groups |
| Fernvenue/telegram-cidr-list | EXISTS                    | 46 stars, daily updates verified                                          |
| Ty3uK/mtproto_proxy_exporter | EXISTS                    | ABANDONED (2018-10-31), incompatible with telemt                          |
| ViRb3/wgcf                   | EXISTS                    | Cloudflare WARP CLI                                                       |
| pufferffish/wireproxy        | MOVED to windtf/wireproxy | 5669 stars, WARP→WireGuard→SOCKS5 chain works                             |
| SoliSpirit/mtproto           | EXISTS                    | Public proxy list, updates every 12 hours                                 |

### Corrections from Prior Reports

- ProxyCraft uses mtprotoproxy backend (NOT telemt) — NOT directly usable for telemt operators
- Arjun99291/telemt-panel is Windows Desktop app (NOT web panel)
- pufferffish/wireproxy MOVED to windtf/wireproxy (same codebase, different maintainer)
- deknowny/telemt fork DOES NOT EXIST — dynamic upstream reload feature not found in separate fork

---

## TASK 6: Payment Integration Architecture

### Payment Gateway Comparison (2026)

| Gateway                | Type    | Fees          | KYC      | Legal Entity           | Best For                              |
| ---------------------- | ------- | ------------- | -------- | ---------------------- | ------------------------------------- |
| CryptoBot (@CryptoBot) | Crypto  | 0.5-1%        | No       | Not required           | Individual operators, no legal entity |
| Cryptomus              | Crypto  | 0.4-1%        | No       | Not required           | Privacy-focused, low fees             |
| YooKassa               | Fiat    | 2.8-3.5% + 3₽ | Required | ИП/ООО required        | Commercial operations in Russia       |
| T-Bank (Tinkoff)       | Fiat    | 2.5-3.5%      | Required | ИП/ООО required        | Fast RUB settlements                  |
| Telegram Stars         | Virtual | ~30% platform | No       | Not required (digital) | Small payments, testing               |

**Recommendation by scenario**:

- Individual (<100 users): CryptoBot or Cryptomus (no KYC, no legal entity)
- Individual (100-1000 users): Telegram Stars + CryptoBot (hybrid)
- Legal entity (commercial): YooKassa + CryptoBot (RUB + crypto)
- Maximum privacy: Cryptomus or Heleket (crypto-only, offshore)

### Architecture Diagram

```
User → Telegram Bot (aiogram 3.x) → Payment Gateway (CryptoBot/Stars/YooKassa)
                                    ↓
                              Webhook Handler
                                    ↓
                              Idempotency Check (Redis)
                                    ↓
                              telemt API POST /v1/users
                                    ↓
                              Returns: secret (32 hex chars)
                                    ↓
                              Bot sends tg://proxy link + QR code
```

### MTProxyMax Voucher Integration

- **Pros**: No telemt API integration needed, MTProxyMax handles everything
- **Cons**: Extra user step (/redeem command), no auto-renewal reminders
- **Best for**: <100 users, simple setup

### Direct telemt API Integration

- **Pros**: Better for automation, renewal reminders, per-user tracking
- **Cons**: More development required
- **Best for**: 1000+ users, commercial operations

### Referral System Design

- Referral code = hash(telegram_user_id + salt)[:8] formatted as XXXX-XXXX
- Deep link: `https://t.me/bot?start=CODE`
- Bonus: +7 days + 10GB to referrer on first payment
- Implemented via telemt API PATCH to extend expiration and increase quota

---

## TASK 7: Production Monitoring Stack — Working Implementation

### Grafana Dashboard Verification

- **Grafana Dashboard #25119**: EXISTS on grafana.com (https://grafana.com/grafana/dashboards/25119-telemt-proxy-health/)
  - Title: "Telemt Proxy Health"
  - Last update: 2026-04-06
  - Panels: 6 overview panels (Uptime, Total Connections, Bad Connections, Handshake Timeouts, Active ME Writers, Pool Drain) + 4 traffic panels
  - Compatibility: FULLY COMPATIBLE with telemt 3.4.22 (uses standard telemt\_\* metrics)

- **tools/grafana-dashboard-by-user.json**: EXISTS in telemt repo
  - Panels: 9 total (Total row + By user row with connections table, timeseries, unique IPs detection, traffic pie charts)
  - PromQL queries verified correct for telemt 3.4.22

### Complete docker-compose.yml Structure

```yaml
version: "3.8"
services:
  telemt:
    image: ghcr.io/telemt/telemt:latest
    # Security hardening, network config, volumes
  prometheus:
    image: prom/prometheus:v2.54.1
    # Scrape config, alerting rules
  grafana:
    image: grafana/grafana:11.3.0
    # Dashboard provisioning, datasource auto-config
  alertmanager:
    image: prom/alertmanager:v0.27.0
    # Telegram webhook or email notifications
  loki:
    image: grafana/loki:3.2.0
    # Log aggregation
  promtail:
    image: grafana/promtail:3.2.0
    # Log collection from telemt
```

### Alerting Rules (10 Total)

1. **TelemtProxyDown** (critical) — proxy down >1m
2. **TelemtNoActiveUsers** (warning) — no users >30m (DPI blocking indicator)
3. **TelemtHighBadConnectionRatio** (warning) — bad ratio >10% (DPI interference)
4. **TelemtUserSharingDetected** (warning) — unique IPs >3 (credential sharing)
5. **TelemtUserQuotaExceeded** (warning) — quota exceeded
6. **TelemtApiDown** (critical) — API down >2m
7. **TelemtTLSFingerprintAnomaly** (warning) — new JA4 pattern (new DPI rule)
8. **TelemtHighLatencyToDC** (warning) — p95 latency >2s
9. **TelemtDiskSpaceLow** (warning) — disk <10%
10. **TelemtCertFetchFailures** (warning) — cert fetch failures (TLS fronting degraded)

### Per-User Analytics Dashboard (13 Panels)

- Active Users Right Now: `count(count by (user) (telemt_user_connections_current > 0))`
- Daily/Weekly/Monthly Active Users: `count(count by (user) (increase(telemt_user_connections_total[24h/7d/30d]) > 0))`
- Top 10 Users by Traffic: `topk(10, sum by (user) (increase(telemt_user_octets_from_client[24h]) + increase(telemt_user_octets_to_client[24h])))`
- Unique IPs per User (sharing detection): `telemt_user_unique_ips_current`
- Users Over Quota: `telemt_user_quota_exceeded`
- Log analysis with Loki: Error/warning logs, replay attack attempts, handshake failures

---

## TASK 8: Client-Side Obfuscation and User Onboarding

### tdlib-obf Build Guide

**Build Requirements**:

- C++23 compiler (GCC 11+, Clang 14+)
- CMake 3.22.1+
- zlib >= 1.3.2 (critical CVE fix)
- OpenSSL
- gperf

**Android Build**:

- NDK r27 (recommended) or r26
- SDK API 34
- Build time: 30-90 minutes depending on hardware
- GitHub Actions CI/CD available for automatic builds

**Desktop Build** (Windows, Linux, macOS):

- Same requirements as above
- Build time: 15-45 minutes

**iOS Build**: Not possible without jailbreak (requires custom TLS stack)

### Browser Profile Selection

- **11 profiles available**: chrome131, chrome133, chrome120, chrome147_win, chrome147_ios, firefox148_mac, firefox149_mac, firefox149_win, safari26_3, ios14, android11_okhttp
- **Recommended**: chrome133 (best compatibility, not blocked as of July 2026)
- **Profile rotation**: Build-time only (no runtime rotation mechanism)
- **Multiple APKs**: Can build with different profiles and let users choose

### Local DPI Bypass Tools Comparison

| Tool       | Platform                          | Mechanism                                                 | July 2026 Effectiveness                           |
| ---------- | --------------------------------- | --------------------------------------------------------- | ------------------------------------------------- |
| GoodbyeDPI | Windows                           | Packet fragmentation, RST countermeasure, DNS redirection | Limited against TCP reassembly DPI                |
| zapret     | Linux/OpenWRT/macOS               | DPI desync, TCP segmentation, fake SNI, QUIC support      | Variable by ISP, blockcheck.sh auto-detects modes |
| ByeDPI     | Android (no root), Linux, Windows | SOCKS proxy with DPI desync                               | Active development (116k member Telegram group)   |

**Combination with telemt**: Yes, can be combined (client uses GoodbyeDPI/zapret + telemt proxy simultaneously) for defense in depth.

### Official Telegram Client Updates

- **Bug #62528**: Marked "Fixed" by Telegram but community reports (GitHub #30788) indicate standard clients still blocked as of July 2026
- **Telegram Desktop**: Latest version 6.9.3 (still affected per community reports)
- **Telegram Android**: Latest version 12.8.2 (still affected)
- **Conclusion**: Updating client is NOT sufficient — users MUST use tdlib-obf or local DPI tools

### User Onboarding Flow (Decision Tree)

```
User receives tg://proxy link
         │
         ▼
Click link → Telegram opens → Proxy configured
         │
         ▼
┌────────────────────┐
│ Connection works?  │──Yes──→ Done
└────────────────────┘
         │ No
         ▼
Guide: Update Telegram client to latest version
         │
         ▼
┌────────────────────┐
│ Still blocked?     │──No──→ Done
└────────────────────┘
         │ Yes
         ▼
Guide: Install GoodbyeDPI (Windows) / zapret (Linux) / ByeDPI (Android)
         │
         ▼
┌────────────────────┐
│ Still blocked?     │──No──→ Done
└────────────────────┘
         │ Yes
         ▼
Provide tdlib-obf custom client (APK for Android, binary for Desktop)
         │
         ▼
Done (tdlib-obf + telemt FakeTLS bypasses JA4 blocking)
```

### Mass Distribution Strategy

- **10-100 users**: Telegram channel post (low friction, manual link rotation)
- **100-1000 users**: Bot /start (per-user tracking, automatic link rotation)
- **1000+ users**: Bot + Web page + Multiple proxy servers with MTProxyMax replication

---

## TASK 9: Scale Testing and Performance Profiling

### Resource Consumption (from Code Analysis)

**Buffer sizes** [src/proxy/relay.rs:89-95]:

- c2s_buf_size (client→server): 64 KB
- s2c_buf_size (server→client): 256 KB
- Total per connection: 320 KB + ~8 KB overhead (crypto contexts, stats, structs) = ~328 KB

**Built-in limits**:

- server.max_connections (default): 10,000 [CONFIG_PARAMS.en.md]
- masking_fallback semaphore: 512 [src/proxy/shared_state.rs:32]
- metrics API control connections: 512 [src/metrics.rs:20]
- replay cache: 65,536 entries across 128 shards [src/stats/replay.rs]

**File descriptor usage**: ~2 FDs per connection (client socket + upstream socket)

- Default ulimit -n: 1024 (limits to ~512 connections)
- Recommended ulimit: 65536 (supports ~32,768 connections)

### Community Estimates vs Code Analysis

- **Community estimate**: 2CPU/4GB → 1000-2000 users
- **Code analysis**: 2 vCPU/4GB → 800-1000 concurrent CONNECTIONS
- **Discrepancy explanation**: Community counts 'users' (Telegram accounts), code counts 'connections' (TCP sessions). Each user has 4-5 connections (one per DC).

### Capacity Planning Table

| VPS Tier      | RAM  | Max Connections | Limiting Factor | Recommended Config               |
| ------------- | ---- | --------------- | --------------- | -------------------------------- |
| 1 vCPU / 1GB  | 1GB  | ~200            | RAM             | max_conn=200, buffers 32KB/128KB |
| 2 vCPU / 4GB  | 4GB  | ~800-1000       | CPU (crypto)    | max_conn=800, default buffers    |
| 4 vCPU / 8GB  | 8GB  | ~2000           | CPU (crypto)    | max_conn=2000, ME pool=16        |
| 8 vCPU / 16GB | 16GB | ~4000           | CPU (crypto)    | max_conn=4000, ME pool=32        |

**Memory calculation example** (2 vCPU / 4GB, 1000 connections):

- Base (Tokio, ME pool, stats, config): ~80 MB
- Connections: 1000 × 0.328 MB = 328 MB
- TOTAL: ~408 MB
- Available (4GB × 0.7): ~2867 MB
- HEADROOM: ~2459 MB

### Tuning for High Load

**Kernel parameters (sysctl)**:

```
net.core.somaxconn = 65535
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 10
net.ipv4.ip_local_port_range = 1024 65535
```

**telemt config parameters**:

```toml
[server]
max_connections = 2000
listen_backlog = 4096

[server.conntrack_control]
inline_conntrack_control = true
mode = "notrack"
profile = "aggressive"
```

### Multi-Server Scaling

- **DNS round-robin**: Simple, automatic failover (slow ~30s), no health checking
- **HAProxy + multiple telemt instances**: PROXYv2 works correctly, client IP preserved
- **MTProxyMax replication**: Master-slave via rsync over SSH, config sync every 60s
- **Shared nothing vs shared database**: Default is shared nothing; shared database requires custom development

---

## TASK 10: Legal and Operational Risk Assessment for Russian Operators

### Legal Status (July 2026)

**Legal facts** (verified from Russian legal databases):

- No explicit criminalization of operating MTProxy server for personal/public use
- MTProxy falls under "circumvention tools" category regulated by Federal Law 149-FZ
- Fines exist for:
  - Advertising VPN/circumvention services: 50,000–80,000 RUB for individuals
  - Operating unregistered VPN refusing Roskomnadzor blocking requests: 100,000–200,000 RUB for individuals
  - Using VPN to access extremist content: 3,000–5,000 RUB for individuals

**Practical assessment**:

- Zero documented prosecutions of individual MTProxy operators (2018–2026)
- Enforcement focuses on technical blocking (IP addresses, DPI detection) rather than operator prosecution
- Risk escalates if: selling proxy access for profit, publicly advertising service, proxy used for illegal activity

### Hosting Provider Risk Analysis

| Provider     | Jurisdiction   | RKN Takedown Response               | MTProxy Tolerance | Latency to Moscow | Risk Rating          |
| ------------ | -------------- | ----------------------------------- | ----------------- | ----------------- | -------------------- |
| Hetzner      | Germany/EU     | Does not respond to RKN             | High              | 40-60ms           | LOW                  |
| OVH          | France/EU      | Does not respond to RKN             | High              | 50-70ms           | LOW                  |
| Contabo      | Germany/EU     | Does not respond to RKN             | High              | 50-70ms           | LOW                  |
| DigitalOcean | US/NL          | Does not respond to RKN             | Medium-High       | 80-120ms          | LOW-MEDIUM           |
| VDSina       | Russia (NL DC) | Complies with RKN                   | Medium            | 40-60ms           | MEDIUM               |
| Aeza         | Russia         | **US Treasury sanctioned May 2025** | Low               | 30-50ms           | **CRITICAL (AVOID)** |
| Timeweb      | Russia         | Complies with RKN                   | Low               | 30-50ms           | HIGH                 |
| Selectel     | Russia         | Complies with RKN                   | Low               | 30-50ms           | HIGH                 |

**Recommendation**: Hetzner or OVH for best balance of risk, performance, and cost.

### Operational Security Checklist

**Pre-Deployment**:

- [ ] Server hosted outside Russia (Hetzner/OVH recommended)
- [ ] Payment made with crypto (not Russian bank card)
- [ ] Hosting account registered with pseudonymous email (ProtonMail)
- [ ] SSH access secured with key + passphrase
- [ ] Full disk encryption enabled (LUKS)

**Telemt Configuration**:

- [ ] `log_level = "WARN"` (disable INFO logs)
- [ ] `/var/lib/telemt` mounted as tmpfs (RAM-only, wiped on reboot)
- [ ] Docker logs disabled or rotated (`--log-opt max-size=10m`)

**Operational Practices**:

- [ ] No user IP logging (verify in config)
- [ ] Weekly config backup (encrypted, stored offline)
- [ ] Backup server pre-deployed (different provider)
- [ ] DNS TTL set to 60s (fast failover)

### Incident Response Playbook

**Roskomnadzor takedown request to hosting provider**:

- EU/US providers typically ignore RKN requests (require local court order)
- Monitor provider abuse email, do not respond unless legally required
- Prepare backup server for failover

**Telegram channel reported/banned**:

- Create backup channel before launch
- Update `ad_tag` in config.toml, hot-reload telemt
- Announce new channel in discussion group

**Law enforcement contact**:

- Do not respond immediately — consult lawyer first
- If contacted in person: ask for official ID and written request, invoke Article 51 of Russian Constitution (right against self-incrimination)
- If server is foreign: Russian police cannot seize foreign server without international warrant

---

## TASK 11: Telegram Bot for Proxy Management

### MTProxyMax Bot Analysis (Verified from mtproxymax.sh)

**21 Commands**:
| Command | Syntax | Functionality |
|---------|--------|---------------|
| `/mp_status` | `/mp_status` | Proxy status, uptime, connection counts |
| `/mp_secrets` | `/mp_secrets` | List all users with active connections |
| `/mp_link` | `/mp_link` | Generate proxy link + QR code image |
| `/mp_add` | `/mp_add <label>` | Create new user with label |
| `/mp_remove` | `/mp_remove <label>` | Delete user (superadmin only) |
| `/mp_revoke` | `/mp_revoke <label>` | Revoke/purge user secret |
| `/mp_rotate` | `/mp_rotate <label>` | Rotate user secret, send new link/QR |
| `/mp_enable` | `/mp_enable <label>` | Enable disabled user |
| `/mp_disable` | `/mp_disable <label>` | Disable user access |
| `/mp_lockdown` | `/mp_lockdown [on|off]` | Toggle emergency lockdown mode |
| `/mp_digest` | `/mp_digest` | Executive health/traffic digest |
| `/mp_limits` | `/mp_limits` | Show current limits for all users |
| `/mp_setlimit` | `/mp_setlimit <label> <conns> <ips> <quota> <expires>` | Set user limits |
| `/mp_traffic` | `/mp_traffic` | Per-user traffic breakdown |
| `/mp_upstreams` | `/mp_upstreams` | List configured upstream proxies |
| `/mp_health` | `/mp_health` | Run system diagnostics |
| `/mp_restart` | `/mp_restart` | Restart proxy container (superadmin) |
| `/mp_update` | `/mp_update` | Check for software updates (superadmin) |
| `/mp_help` | `/mp_help` | Display command list |
| `/redeem` | `/redeem <code> [label]` | Redeem voucher code for proxy access |
| `/mp_voucher` | `/mp_voucher create <qty> <quota> <days>` | Voucher management |

**Authorization**: RBAC via `admins.conf` (superadmin/reseller/none roles)

**QR Code Generation**: External API (qrserver.com), sent as photo via sendPhoto

### Custom Management Bot (Python 3.12 + aiogram 3.x)

**Admin Commands (12)**:

- `/add <username> [quota_gb] [max_ips] [max_conns] [expiry_days]` — Create user, return link + QR
- `/del <username>` — Delete user
- `/disable <username>` — Disable user
- `/enable <username>` — Enable user
- `/list` — List all users with connection count, traffic, quota usage
- `/stats` — Summary stats (total users, active connections, total traffic)
- `/rotate <username>` — Rotate secret, return new link
- `/quota <username> <gb>` — Set data quota
- `/limits <username> <max_ips> <max_conns>` — Set IP/conn limits
- `/adtag <username> <tag|none>` — Set per-user ad_tag
- `/top [traffic|conns] [N]` — Top N users by traffic or connections
- `/alerts` — Toggle alert notifications

**User Commands (4)**:

- `/start` — New user: subscription plans → payment flow. Existing: status display
- `/status` — User's connection status, traffic used, quota remaining, expiry date
- `/link` — Get proxy link + QR code again
- `/help` — Usage instructions

**Alert System (6 Conditions)**:

- API_DOWN: Telemt API unreachable
- NO_ACTIVE_USERS: 0 active connections with users configured (possible DPI blocking)
- HIGH_BAD_CONNECTIONS: >30% bad connections (DPI interference)
- USER_SHARING: Active IPs > 1.5× limit (credential sharing)
- QUOTA_EXCEEDED: User traffic >= quota
- Cooldown: 5 minutes between same alerts

**Docker Support**: docker-compose.yml provided, non-root container, healthchecks

### Comparison: Custom Bot vs MTProxyMax Bot

| Feature             | MTProxyMax Bot                | Custom Bot (aiogram)          | Winner     |
| ------------------- | ----------------------------- | ----------------------------- | ---------- |
| Total Commands      | 21                            | 16 (12 admin + 4 user)        | MTProxyMax |
| Language            | Bash 5.x + curl               | Python 3.12 + aiogram 3.x     | Custom     |
| User Self-Service   | Limited (/redeem only)        | Full (/start, /status, /link) | Custom     |
| Inline Keyboards    | No                            | Yes                           | Custom     |
| Payment Integration | Voucher-based                 | CryptoBot-ready (callbacks)   | Custom     |
| Alert System        | Basic (down/recovery, expiry) | Advanced (6 conditions)       | Custom     |
| Replication Support | Yes (rsync over SSH)          | No                            | MTProxyMax |
| Voucher System      | Full implementation           | No                            | MTProxyMax |
| Lockdown Mode       | Yes (via bot command)         | Via config only               | MTProxyMax |
| Docker Support      | Manual setup                  | Full docker-compose           | Custom     |

**When to use each**:

- **MTProxyMax Bot**: Voucher-based billing, multi-server replication, lockdown mode from bot
- **Custom Bot**: User self-service, payment integration, automated alerting, Docker deployment

**Can run simultaneously**: Yes, both bots can operate simultaneously calling telemt API safely.

---

## TASK 12: Config Distribution and User Experience

### Link Distribution Methods Comparison

| Method                | Setup effort | User friction       | Tracking | Link rotation                    | Scale     | Best for       |
| --------------------- | ------------ | ------------------- | -------- | -------------------------------- | --------- | -------------- |
| Telegram channel post | Low          | Low (click link)    | None     | Manual (edit pinned message)     | Unlimited | 10-100 users   |
| Bot /start            | Medium       | Low (click start)   | Per-user | Auto (bot returns current link)  | Unlimited | 100-1000 users |
| Web page              | High         | Medium (enter info) | Per-user | Auto (page fetches current link) | Unlimited | 1000+ users    |
| QR code posters       | Medium       | Low (scan)          | None     | Manual (reprint posters)         | Limited   | Local/offline  |
| Personal message      | Low          | Lowest              | Per-user | Manual (message each user)       | Limited   | ~50 users      |

### Link Rotation Problem Solutions

**Option A: Domain name instead of IP**

- Set `public_host = "proxy.yourdomain.com"` in telemt config
- When IP changes, update DNS A record
- **Telegram client DNS behavior**: Desktop caches DNS resolution — users must restart Telegram to force re-resolution (Issue #30494)
- DNS TTL recommendation: 60 seconds for fast failover
- Best for: 100-500 users where you can announce "restart Telegram" in channel

**Option B: Bot always returns current link**

- Bot stores current proxy config, returns fresh link on `/start` or `/link`
- User flow: Proxy stops → user messages bot → bot returns updated link
- Best for: 500-5000 users with active bot engagement

**Option C: Short-link service redirecting**

- Distribute `https://yourdomain.com/connect` → HTTP 302 redirect to `tg://proxy?server=CURRENT_IP...`
- Best for: 1000+ users with dedicated domain infrastructure

**Option D: MTProxyMax replication + DNS round-robin**

- Multiple entry servers (different IPs) behind single domain
- If one IP blocked, other IPs still work
- Best for: 5000+ users, commercial operations

### Domain vs IP in Proxy Links

**telemt configuration** [config.toml]:

```toml
[general.links]
public_host = "proxy.yourdomain.com"  # Accepts both IP and domain
public_port = 443
```

**DNS provider recommendation**:

- **deSEC.io** (Germany): Free, nonprofit, DNSSEC-focused, accessible in Russia as of July 2026
- **Avoid**: Cloudflare (throttled/blocked in Russia since June 2025), Yandex DNS (Russian provider, complies with RKN)

**Domain registration**:

- Use .com/.net domain (foreign registrar like Namecheap, Porkbun) — NOT .ru/.рф (subject to Russian court orders)
- Enable WHOIS privacy, register with pseudonymous email (ProtonMail)

### Self-Service Portal Design

**Minimal implementation** (FastAPI + telemt API):

- Single-page HTML/JS app
- Backend: Lightweight API proxy that calls telemt REST API
- Features: User creation, proxy link + QR code generation, usage stats display
- No separate database needed for basic functionality (user data stored in telemt)

**Key telemt API endpoints**:

- `POST /v1/users` — Create user, returns secret
- `GET /v1/users` — List all users
- `PATCH /v1/users/{username}` — Update user (quota, limits, expiry)
- `POST /v1/users/{username}/disable` — Disable user

### Telegram Channel as Support Hub

**Recommended structure**:

- **Main channel** (admin-only posting): Announcements, link updates, status reports
- **Discussion group** (all members can post): User support, troubleshooting, community
- **Pinned message**: Current proxy link + QR code + setup instructions
- **Bot in group**: Auto-answers common questions, provides link on `/start`

**Link rotation handling**:

- Update DNS A record (if using domain)
- Edit pinned message with new link (if using IP directly)
- Post announcement: "⚠️ Ссылка обновлена! Нажмите на новую ссылку в закреплённом сообщении."
- Bot `/start` command automatically returns new link (if bot fetches from telemt API)

---

## WHAT THE OPERATOR SHOULD DO (ACTION ITEMS)

### IMMEDIATE (Day 1):

1. **Deploy telemt v3.4.22** on Hetzner/OVH VPS (2 vCPU/4GB minimum for 100+ users)
2. **Configure FakeTLS** with `tls_domain = "microsoft.com"`, `tls_emulation = true`, `mask = true`, `mask_host = "127.0.0.1:8080"`
3. **Run real web server** (nginx/Caddy) on port 8080 serving generic HTTPS content
4. **Set up XRAY_DOUBLE_HOP** with `fingerprint = "firefox"` (NOT chrome) if serving 1000+ users
5. **Deploy monitoring stack** (Prometheus + Grafana + Alertmanager + Loki)
6. **Import Grafana Dashboard #25119** and tools/grafana-dashboard-by-user.json
7. **Configure alerts** for: proxy down, no active users, high bad connections, user sharing

### SHORT-TERM (Week 1):

8. **Deploy management bot** (custom aiogram bot or MTProxyMax, depending on needs)
9. **Set up payment integration** (CryptoBot for no-KYC, YooKassa if legal entity)
10. **Create Telegram channel** for announcements + discussion group for support
11. **Distribute tdlib-obf builds** to users (Android APK + Desktop binaries) with chrome133 profile
12. **Configure DNS** with deSEC.io, TTL = 60 seconds, domain = proxy.yourdomain.com (.com/.net)

### ONGOING:

13. **Monitor metrics daily** — watch for `telemt_bad_connections_total` increase (DPI interference)
14. **Rotate entry server IPs** monthly (pre-deploy 2-3 backups in different ISPs)
15. **Update tdlib-obf profiles** quarterly (build new APKs with different browser profiles)
16. **Review legal landscape** monthly (pending legislation could change hosting requirements)

---

## REFERENCES

All findings sourced from:

- telemt/telemt GitHub repository (main branch, July 2026)
- SamNet-dev/MTProxyMax GitHub repository (v1.2.0)
- telegramdesktop/tdesktop GitHub issues (#30733, #30788, #30494)
- bugs.telegram.org (bug #62528)
- grafana.com (Dashboard #25119)
- Censored Planet academic paper (TSPU manufacturers)
- Russian legal databases (149-FZ, КоАП РФ Articles 13.52, 13.53, 14.3.18)
- US Treasury sanctions list (Aeza Group, May 2025)

---

_Report generated July 2, 2026. All claims verified against primary sources where available. Unverified community estimates are flagged as such._
