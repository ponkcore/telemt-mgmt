# telemt-mgmt Test Deploy Report (2nd run)

**Date:** 2026-07-04
**Author:** Kitsune
**Repo:** github.com/ponkcore/telemt-mgmt @ `9674c7d` (ARCH-001@0.2.1)
**Servers:** VPSVILLE-test (entry, RU) + HETZNER-test (exit, EU)
**GitHub Issue:** [#43](https://github.com/ponkcore/telemt-mgmt/issues/43)

---

## 1. Summary

Second test deployment after repo bugfixes (TKT-020/021/022/023).
All 12 bugs from the first deployment are fixed in the repo.
The architectural gap (#11 — tg://proxy vs VLESS-Reality) is resolved:
entry inbound changed from VLESS-Reality to dokodemo-door (TKT-020).

**Result:** Deploy succeeded without manual workarounds for the first
12 bugs. 5 new bugs found (N1-N5). The critical blocker (N4) is a
`www.microsoft.com` incompatibility with Xray uTLS Reality handshake
— changing SNI to `ads.x5.ru` resolves it. After all fixes, the
double-hop tunnel works: `tg://proxy` links connect through
entry:443 → VLESS-Reality → exit → telemt → Telegram DCs.

---

## 2. What Changed Since First Deploy

| Commit | Ticket | Summary |
|--------|--------|---------|
| `7c7c00b` | TKT-020 | ARCH-001@0.2.1: dokodemo-door replaces VLESS-Reality on entry |
| `eda986e` | TKT-020 | Entry xray-config.json.template: two-stage dokodemo-door |
| `8df5327` | TKT-023 | Deploy blockers D1-D8: Angie image, mount paths, caps, INFRA_DIR |
| `5de9d7f` | TKT-022 | Infra bugfixes: .env.example, migrate.sh health check |
| `18a1a74` | TKT-021 | Code bugfixes: async, JWT, DB factory, CORS, ProxyConfig |
| `40276a5` | — | ARCH-001@0.2.1 status: approved (PO approval) |

---

## 3. Bug Status: Previous 12 → Now

| # | Issue | Status | How |
|---|-------|--------|-----|
| 1 | `angie/angie:latest` doesn't exist | Fixed | `docker.angie.software/angie:1.8.1-alpine` (official registry) |
| 2 | Xray mount path `/etc/xray/` | Fixed | `/usr/local/etc/xray/config.json:ro` |
| 3 | telemt config not loaded | Fixed | `command: ["/etc/telemt/config.toml"]` |
| 4 | `config_strict` + quota key | Fixed | `access.user_data_quota_bytes` removed from template |
| 5 | Xray can't bind :443 | Fixed | `user: "0:0"` on xray services |
| 6 | Angie chown/setgid crash | Fixed | `CHOWN,SETGID,SETUID` caps, `read_only` removed, tmpfs for cache |
| 7 | `INFRA_DIR` path `../..` → `..` | Fixed | `SCRIPT_DIR/..` in all deploy scripts |
| 8 | `xray x25519` double command | Fixed | Extra `xray` prefix removed |
| 9 | tls_emulation mask:8080 | Fixed | `mask_port = 443` in third-party mode |
| 10 | proxy_protocol trusted CIDRs | Fixed | `proxy_protocol_trusted_cidrs = ["127.0.0.1/32"]` |
| 11 | **ARCH: tg://proxy ≠ VLESS** | **Resolved** | **dokodemo-door entry (TKT-020)** |
| 12 | API auth docs | Fixed | TKT-022 .env.example updates |

---

## 4. New Bugs Found (N1-N5)

### N1. telemt read_only + /app writable files

**Severity:** Medium (causes unhealthy + log spam)
**Symptom:**
```
WARN telemt::maestro::runtime_tasks: Failed to flush beobachten snapshot
  error=Read-only file system (os error 30) path=beobachten.txt
WARN telemt::maestro::helpers: Failed to store startup proxy-config cache
  error=Permission denied (os error 13) path="cache/proxy-config-v4.txt"
```
Repeating every 15s. Healthcheck reports `unhealthy` (failing streak: 3).

**Root cause:** telemt writes `beobachten.txt` and `cache/` to its
working directory `/app/` (not to mounted volumes). With
`read_only: true`, writes fail. Container runs as non-root (image
default), so even without `read_only`, `/app/` is root-owned.

**Fix applied (test):** `user: "0:0"` + removed `read_only: true` on
telemt service (same pattern as xray-exit).

**Suggested fix for repo:** In `infra/exit/docker-compose.yml`, telemt
service: add `user: "0:0"`, remove `read_only: true`.

### N2. telemt healthcheck uses /app/config.toml

**Severity:** Medium (healthcheck fails → unhealthy)
**Symptom:** Healthcheck.Test =
`["CMD", "/app/telemt", "healthcheck", "/app/config.toml", "--mode",
"liveness"]`. Looks for config at `/app/config.toml`, but D3 fix mounts
to `/etc/telemt/config.toml` and `command:` overrides runtime path.

**Fix applied (test):** Added volume mount
`./config/config.toml:/app/config.toml:ro`.

**Suggested fix for repo:** Either add the mount, or override healthcheck
in compose with `/etc/telemt/config.toml` path.

### N3. tls_emulation fetch fails (non-blocking)

**Severity:** Low
**Symptom:**
```
WARN telemt::tls_front::fetcher: Raw TLS fetch attempt failed
  sni=www.microsoft.com error=Connection reset by peer (os error 104)
```
**Impact:** Non-blocking. telemt falls back to built-in fake cert.
Proxy works.

### N4. `www.microsoft.com` breaks VLESS-Reality handshake (BLOCKER)

**Severity:** Blocker — VLESS-Reality tunnel entry→exit never establishes
**Symptom:**
Exit xray logs:
```
REALITY: processed invalid connection from <ENTRY_IP>:<port>: failed to read client hello
```
Entry xray logs (debug):
```
dialing TCP to tcp:168.119.59.155:443
dialing to tcp:168.119.59.155:443
```
Then **hangs** — no TLS ClientHello is ever sent.

**Root cause:**
`www.microsoft.com` (served by Akamai CDN) is incompatible with Xray's
uTLS Reality handshake. When the VLESS-Reality outbound uses
`serverName: "www.microsoft.com"` with `fingerprint: "firefox"`, the
uTLS library hangs during ClientHello generation. TCP connects, but
zero bytes are sent.

Verified with `xray tls ping`:
- Without SNI → handshake succeeds (Reality forwards to dest)
- With SNI=`www.microsoft.com` → **hangs** (timeout)

Tested fingerprints: `firefox`, `chrome`, `safari`, `random` — all hang.
Reproduced with standalone xray binary (not Docker-related).

**Fix applied (test):**
Changed Reality SNI + dest to `ads.x5.ru` on both entry and exit:

| Component | Before | After |
|---|---|---|
| Entry outbound `serverName` | `www.microsoft.com` | `ads.x5.ru` |
| Exit inbound `dest` | `www.microsoft.com:443` | `ads.x5.ru:443` |
| Exit inbound `serverNames` | `["www.microsoft.com"]` | `["ads.x5.ru"]` |

After fix, VLESS-Reality tunnel establishes immediately:
```
proxy/vless/outbound: tunneling request via 168.119.59.155:443
proxy/vless/inbound: firstLen = 1186
from <ENTRY_IP>:44746 accepted [vless-reality-exit-in -> to-telemt]
connection opened to tcp:127.0.0.1:8443
```

**Context:** A VLESS-Reality cascade between the same servers worked
before the telemt-mgmt deploy. That setup used `ads.x5.ru`. The
telemt-mgmt templates changed the default to `www.microsoft.com`,
which broke the tunnel.

**Suggested fix for repo:**
- `infra/exit/deploy-exit.sh`: change `EXIT_REALITY_SNI` default from
  `www.microsoft.com` to `ads.x5.ru`
- `infra/exit/xray-config.json.template`: `dest` and `serverNames`
  will follow the new default automatically
- `infra/entry/xray-config.json.template`: `serverName` uses
  `__EXIT_REALITY_SNI__`, so it propagates automatically

### N5. flow mismatch between entry and exit templates

**Severity:** Medium
**Symptom:** Entry outbound has `flow: "xtls-rprx-vision"` on VLESS
user, exit inbound client does not.

**Fix applied (test):** Removed `flow` from entry outbound (not needed
for transparent TCP relay).

**Suggested fix for repo:** Remove `flow` from entry template, or add
it to exit client template.

---

## 5. Architecture Deployed (0.2.1 — dokodemo-door entry, after fixes)

```
Telegram client
    │
    │  tg://proxy?server=test.dataconflux.org&port=443&secret=ee...
    │  (MTProto/FakeTLS — standard Telegram proxy protocol)
    ▼
[VPSVILLE-test — Entry, RU]
    Xray dokodemo-door inbound (:443, public-in)
        → freedom outbound (proxyProtocol:1, PROXYv1 injection)
        → 127.0.0.1:10444 (tunnel-in, second dokodemo-door)
        → VLESS-Reality outbound → exit:443 (encrypted S2, ADR-009@0.2.1)
        Reality SNI: ads.x5.ru (NOT www.microsoft.com — see N4)
    │
    ▼ (VLESS-Reality encrypted tunnel — entry has NO Reality keys)
[HETZNER-test — Exit, EU]
    Xray-exit VLESS-Reality inbound (:443)
        Reality dest: ads.x5.ru:443, serverNames: ["ads.x5.ru"]
        → freedom outbound (redirect → 127.0.0.1:8443)
    telemt (:8443, FakeTLS)
        TLS domain: www.microsoft.com (telemt FakeTLS — separate from Reality)
        proxy_protocol: true (trusted: 127.0.0.1/32)
        tls_emulation: true (falls back to fake cert — see N3)
        ad_tag: 00000000... (test mode, no ad_tag)
    Angie mask host (:8080)
    telemt API (:9091)
    telemt metrics (:9090)
    │
    ▼
Telegram DCs (RPC handshake OK: DC 2,4,5,-2,-3,-4,-5)
```

### Important distinction: Reality SNI vs FakeTLS domain

- **Reality SNI** (`ads.x5.ru`): used for the entry→exit VLESS-Reality
  tunnel. Must NOT be `www.microsoft.com` (N4).
- **FakeTLS domain** (`www.microsoft.com`): used by telemt for
  client-facing MTProto FakeTLS. This is separate and works fine — it's
  the SNI Telegram clients see when connecting to telemt:8443 directly.
- These two domains are independent and can be different.

---

## 6. Container Inventory

**HETZNER-test (exit):**

| Container | Image | Ports | Status |
|---|---|---|---|
| telemt-exit | ghcr.io/telemt/telemt:latest | :8443, :9091, :9090 | healthy (after N1+N2 fixes) |
| xray-exit | ghcr.io/xtls/xray-core:latest | :443 | Up |
| telemt-mask | docker.angie.software/angie:1.8.1-alpine | :8080 | Up |

**VPSVILLE-test (entry):**

| Container | Image | Ports | Status |
|---|---|---|---|
| telemt-xray-entry | ghcr.io/xtls/xray-core:latest | :443, 127.0.0.1:10444 | Up |

All containers use `network_mode: host`.

---

## 7. Connectivity Verification

| Path | Result |
|---|---|
| test.dataconflux.org DNS | → 45.142.211.242 |
| exit-test.dataconflux.org DNS | → 168.119.59.155 |
| Hermes VPS → entry:443 (TCP) | ✓ |
| Hermes VPS → exit:8443 (TCP) | ✓ |
| Hermes VPS → exit:9091 (API, TCP) | ✓ |
| Entry → exit:443 (VLESS tunnel) | ✓ (after N4 fix) |
| Entry → exit:8443 (TCP) | ✓ |
| telemt API :9091 | ✓ Responding (raw token auth) |
| Xray entry :443 | ✓ Listening (dokodemo-door) |
| Xray exit :443 | ✓ Listening (VLESS-Reality, SNI=ads.x5.ru) |
| telemt :8443 | ✓ Listening (FakeTLS, www.microsoft.com) |
| Angie mask :8080 | ✓ Listening (HTTP) |
| telemt health | ✓ healthy (after N1+N2 fixes) |
| Telegram DCs | ✓ RPC handshake OK (DC 2,4,5,-2,-3,-4,-5) |
| VLESS-Reality tunnel | ✓ Confirmed via exit xray access logs |
| Double-hop path | ✓ entry → VLESS → exit → telemt:8443 |

### Exit xray log evidence (after N4 fix):
```
proxy/vless/inbound: firstLen = 1186
received request for tcp:127.0.0.1:10445
taking detour [to-telemt] for [tcp:127.0.0.1:10445]
from 45.142.211.242:44746 accepted [vless-reality-exit-in -> to-telemt]
connection opened to tcp:127.0.0.1:8443
```

---

## 8. Proxy Links

### Double-hop (through entry — tg://proxy works natively)

```
tg://proxy?server=test.dataconflux.org&port=443&secret=ee000000000000000000000000000000007777772e6d6963726f736f66742e636f6d
```

Client → entry:443 (dokodemo-door) → VLESS-Reality tunnel (SNI=ads.x5.ru)
→ exit → telemt:8443 (FakeTLS, www.microsoft.com) → Telegram DCs.
Standard Telegram proxy — no xray/v2ray client needed.

### Direct (bypass entry, for testing)

```
tg://proxy?server=exit-test.dataconflux.org&port=8443&secret=ee000000000000000000000000000000007777772e6d6963726f736f66742e636f6d
```

### Secret format

```
ee                                                          — TLS mode marker
00000000000000000000000000000000                            — 16 zero bytes (no ad_tag, test mode)
7777772e6d6963726f736f66742e636f6d                          — hex("www.microsoft.com")
```

---

## 9. Files Modified on Servers (test-only patches)

### HETZNER-test: `/opt/telemt-mgmt/infra/exit/`

**docker-compose.yml** (N1+N2 fixes):
- Added `user: "0:0"` to telemt service
- Removed `read_only: true` from telemt service
- Added volume: `./config/config.toml:/app/config.toml:ro`

**xray-config.json** (N4+N5 fixes):
- Changed `dest` from `www.microsoft.com:443` to `ads.x5.ru:443`
- Changed `serverNames` from `["www.microsoft.com"]` to `["ads.x5.ru"]`
- Removed `flow` from client (tested, then kept removed)
- Changed `loglevel` to `info` (for debugging, should be `warning` in production)

### VPSVILLE-test: `/opt/telemt-mgmt/infra/entry/`

**xray-config.json** (N4+N5 fixes):
- Changed `serverName` from `www.microsoft.com` to `ads.x5.ru`
- Removed `flow` from outbound user
- Changed `loglevel` to `warning` (production)

---

## 10. Deploy Sequence (what was done)

1. **Clone repo** (commit 9674c7d) to `/tmp/telemt-mgmt`
2. **Verify server cleanliness** — both servers clean
3. **Recreate DNS** — `test.dataconflux.org` + `exit-test.dataconflux.org` on Cloudflare
4. **Verify Docker images** — all three exist
5. **Package + transfer repo** — tar to both servers, unpack to `/opt/telemt-mgmt/`
6. **Generate keys** — X25519 keypair, VLESS UUID, short IDs, telemt secret, auth header
7. **Pre-fill .env** — exit: 11 vars; entry: 5 vars. Non-interactive deploy.
8. **deploy-exit.sh** — ran on HETZNER-test, 17s. All 3 containers started. No manual workarounds for D1-D8.
9. **deploy-entry.sh** — ran on VPSVILLE-test, 6s. Xray container started.
10. **Fix N1+N2** — patched docker-compose.yml (user:root, remove read_only, add /app/config.toml mount). Health: healthy.
11. **Debug N4** — VLESS-Reality tunnel not establishing. Extensive debugging:
    - Checked key match, SNI, shortId — all correct
    - Tested with/without flow — no difference
    - Tested with simplified config (single dokodemo-door) — same issue
    - Tested standalone xray (no Docker) — same issue
    - Tested different fingerprints (firefox, chrome, safari, random) — all hang
    - Used `xray tls ping` — found SNI=www.microsoft.com hangs, no SNI works
    - Changed SNI to `ads.x5.ru` — **works immediately**
12. **Fix N4** — changed Reality SNI+dest to `ads.x5.ru` on both servers
13. **Fix N5** — removed flow from entry outbound
14. **Verify** — VLESS-Reality tunnel confirmed via exit xray access logs

---

## 11. Debugging Methodology for N4

The N4 blocker took significant debugging. Here's the methodology:

1. **Symptom:** Exit xray logs `failed to read client hello` from entry IP
2. **Hypothesis 1: Docker issue** → Tested standalone xray binary → same issue → ruled out
3. **Hypothesis 2: Default config conflict** → Checked xray image default configs → all empty `{}` → ruled out
4. **Hypothesis 3: Flow mismatch** → Added flow to exit, then removed from both → no change → ruled out
5. **Hypothesis 4: Fingerprint bug** → Tested firefox, chrome, safari, random → all hang → ruled out
6. **Hypothesis 5: Key mismatch** → Verified X25519 keypair matches → ruled out
7. **Key test: `xray tls ping`** → Without SNI: succeeds. With SNI=www.microsoft.com: hangs.
8. **Compared with working setup** → Previous VLESS-Reality cascade used `ads.x5.ru` → changed SNI → **works**
9. **Root cause:** `www.microsoft.com` (Akamai CDN) incompatible with uTLS Reality ClientHello generation

---

## 12. Recommendations

### For the repo (GitHub issue #43)

1. **N4 (BLOCKER):** Change default `EXIT_REALITY_SNI` from `www.microsoft.com` to `ads.x5.ru` in `deploy-exit.sh`
2. **N1:** Add `user: "0:0"` to telemt service, remove `read_only: true`
3. **N2:** Add `./config/config.toml:/app/config.toml:ro` volume to telemt service
4. **N5:** Remove `flow` from entry outbound template (or add to exit client template)
5. **N3:** Investigate tls_emulation fetch failure (low priority, non-blocking)

### For production deployment

1. **ad_tag:** Get from @MTProxybot. Check IP reputation.
2. **UFW:** Already configured by deploy scripts
3. **Swap:** Add 1GB swap on VPSVILLE-test (1GB RAM server)
4. **Self-steal domain:** Consider using exit-test.dataconflux.org as tls_domain
5. **Reality SNI:** Use `ads.x5.ru` (verified working). Do NOT use `www.microsoft.com`.
6. **FakeTLS domain:** `www.microsoft.com` is fine for telemt FakeTLS (client-facing). The N4 issue only affects Reality (entry→exit tunnel).

---

## 13. Key Insight: Reality SNI vs FakeTLS domain

These are **two different domains** serving **two different purposes**:

| Setting | Value | Purpose | Where |
|---|---|---|---|
| Reality SNI | `ads.x5.ru` | Entry→exit VLESS-Reality tunnel camouflage | xray configs (both sides) |
| FakeTLS domain | `www.microsoft.com` | telemt client-facing MTProto FakeTLS | telemt config.toml |

The N4 blocker only affects the Reality SNI. The FakeTLS domain
(`www.microsoft.com`) works fine for telemt's client-facing TLS —
it's a completely separate mechanism.

---

## 14. Skill Update

The `telemt-mgmt-deploy` skill updated to reflect:
- ARCH-001@0.2.1 (dokodemo-door entry)
- All 12 previous bugs marked as fixed
- 5 new bugs (N1-N5) documented
- Architecture section updated for dokodemo-door two-stage design
- N4 root cause and fix documented (www.microsoft.com → ads.x5.ru)
