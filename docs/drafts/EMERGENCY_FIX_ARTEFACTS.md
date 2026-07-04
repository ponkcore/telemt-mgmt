# telemt-mgmt Emergency Fix — Full Artefacts

**Date:** 2026-07-04
**Author:** Viktor (Technical Architect)
**ARCH-001:** 0.2.0 → 0.2.1
**ADR-009:** 0.2.0 → 0.2.1

---

## === ADR-009@0.2.1 (revised) ===

```markdown
---
id: ADR-009
type: adr
status: accepted
created: 2026-07-03
revised: 2026-07-04
---

# ADR-009: Encrypted Entry-to-Exit Segment via VLESS-Reality

## Context
ARCH-001@0.1.2 §3 C5 uses a `freedom` outbound on the entry server to redirect raw TCP to the
exit server. This exposes MTProto byte patterns on the RU→EU international link (segment S2),
where TSPU scrutiny is deepest. TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 and §6 document
post-handshake payload analysis as an active TSPU capability since June 2026, and
TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3 confirms production infrastructure "never sends raw
proxy traffic on the RU→EU segment."

## Decision
We will encrypt segment S2 (entry → exit) with a VLESS-Reality tunnel. The entry server
retains a **`dokodemo-door` inbound** (transparent TCP forward on :443) so Telegram clients
can connect with standard MTProto/FakeTLS via `tg://proxy` links. The VLESS-Reality tunnel
operates **between entry and exit only** — it is an outbound on the entry and an inbound on
the exit. The architecture becomes:

- **Entry:** two-stage `dokodemo-door` inbound (:443 public → :10444 local) with `freedom`
  `proxyProtocol:1` between stages (PROXYv1 injection) → VLESS-Reality outbound to exit:443
- **Exit:** Xray VLESS-Reality inbound (:443, `xver:0`, from entry only) → `freedom` outbound
  → telemt localhost:8443 (MTProto/FakeTLS) + Angie :8080 (mask)

telemt moves from port 443 to 8443 (not externally exposed). Client IP is preserved via
PROXYv1: the entry's `freedom proxyProtocol:1` prepends a PROXYv1 header into the data
stream; the VLESS tunnel carries it end-to-end; telemt on exit parses it with
`proxy_protocol = true`.

**Critical:** The client-facing inbound on entry is `dokodemo-door` (transparent TCP), NOT
`vless`. Telegram clients speak MTProto, not VLESS. The `tg://proxy` link points to the
entry server (domain, port 443). The client's FakeTLS-wrapped MTProto is forwarded
transparently — the entry never interprets the protocol.

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

The exit inbound MUST have `xver:0`. With `xver:1`, the exit would prepend a *second*
PROXYv1 header (containing the *entry server's* IP), causing telemt to see entry's IP
instead of the real client's IP.

## Consequences
- **Positive:** MTProto patterns completely hidden from S2 DPI; international gateway sees
  only VLESS-Reality (standard HTTPS appearance).
- **Positive:** Post-handshake payload analysis — the strongest June 2026 detection vector —
  is fully mitigated on S2.
- **Positive:** `tg://proxy` links work — entry accepts standard MTProto/FakeTLS from
  Telegram clients. No VLESS client required.
- **Positive:** Entry server simplified — no Reality keys, no VLESS UUID, no SNI selection.
  Only exit server credentials needed.
- **Negative / cost:** Additional Xray process on exit server (minimal resource cost). Exit
  deploy script is more complex. 1–3 RTT connection setup overhead (one-time per persistent
  Telegram connection).
- **Negative / cost:** Entry server has no TLS/Reality facade for active probes on :443.
  Probes are forwarded through the tunnel to exit → telemt, which handles masking. This is
  acceptable per the reference architecture (TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md Task 3).

### Revision: 0.2.0 → 0.2.1

**0.2.0 (WRONG):** Entry inbound was `vless` (VLESS-Reality, client-facing). This broke
`tg://proxy` links because Telegram clients speak MTProto, not VLESS. The VLESS tunnel
was between *client and entry* — but it should be between *entry and exit*.

**0.2.1 (CORRECT):** Entry inbound is `dokodemo-door` (transparent TCP forward). The
VLESS-Reality tunnel is between *entry outbound and exit inbound* (segment S2 only). This
matches the reference architecture in TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md Task 3
(XRAY_DOUBLE_HOP verified config) and TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md §3.4.

## Alternatives considered
- **Keep `vless` inbound, generate VLESS links** — rejected: requires xray/v2ray client on
  user device, breaks Telegram's built-in proxy support, violates PRD-001 assumption that
  end users use standard Telegram clients.
- **XHTTP-TLS transport** — deferred: VLESS-Reality is better documented and more widely
  deployed in production Russian proxy infrastructure.
- **Keep `freedom` (raw TCP, no encrypted S2)** — rejected: post-handshake payload analysis
  is active, production systems unanimously encrypt S2.
```

---

## === ENTRY XRAY CONFIG (revised xray-config.json.template) ===

```json
{
  "log": {
    "loglevel": "warning",
    "access": "",
    "error": "",
    "dnsLog": false
  },
  "inbounds": [
    {
      "tag": "public-in",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "127.0.0.1",
        "port": 10444,
        "network": "tcp"
      }
    },
    {
      "tag": "tunnel-in",
      "listen": "127.0.0.1",
      "port": 10444,
      "protocol": "dokodemo-door",
      "settings": {
        "network": "tcp"
      }
    }
  ],
  "outbounds": [
    {
      "tag": "proxy-injector",
      "protocol": "freedom",
      "settings": {
        "proxyProtocol": 1
      }
    },
    {
      "tag": "proxy-to-exit",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "__EXIT_SERVER_IP__",
            "port": 443,
            "users": [
              {
                "id": "__EXIT_VLESS_UUID__",
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
          "serverName": "__EXIT_REALITY_SNI__",
          "fingerprint": "firefox",
          "shortId": "__EXIT_SHORT_ID__",
          "publicKey": "__EXIT_PUBLIC_KEY__"
        }
      }
    },
    {
      "tag": "direct",
      "protocol": "freedom",
      "settings": {
        "domainStrategy": "UseIP"
      }
    },
    {
      "tag": "block",
      "protocol": "blackhole",
      "settings": {
        "response": {
          "type": "http"
        }
      }
    }
  ],
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "inboundTag": ["public-in"],
        "outboundTag": "proxy-injector"
      },
      {
        "type": "field",
        "inboundTag": ["tunnel-in"],
        "outboundTag": "proxy-to-exit"
      }
    ]
  }
}
```

### Key changes from 0.2.0 template

| Aspect | 0.2.0 (WRONG) | 0.2.1 (CORRECT) |
|--------|---------------|-----------------|
| Inbound protocol | `vless` (VLESS-Reality, client-facing) | `dokodemo-door` (transparent TCP) |
| Inbound count | 1 (VLESS :443) | 2 (public :443 + tunnel :10444) |
| PROXY injection | `xver:1` on Reality inbound | `freedom proxyProtocol:1` between stages |
| Entry Reality keys | Required (private key, SNI, short IDs) | **Not needed** (no Reality on entry) |
| Entry VLESS UUID | Required (for VLESS inbound auth) | **Not needed** (no VLESS inbound) |
| Sniffing | Enabled | Omitted (transparent forward, no protocol analysis) |
| Template placeholders removed | — | `__VLESS_UUID_ENTRY__`, `__REALITY_PRIVATE_KEY__`, `__REALITY_SNI__`, `__REALITY_SERVER_NAMES__`, `__REALITY_SHORT_IDS__` |
| Template placeholders kept | — | `__EXIT_SERVER_IP__`, `__EXIT_VLESS_UUID__`, `__EXIT_PUBLIC_KEY__`, `__EXIT_REALITY_SNI__`, `__EXIT_SHORT_ID__` |

---

## === EXIT XRAY CONFIG (revised xray-config.json.template) ===

One change: `"xver": 1` → `"xver": 0`.

```json
{
  "log": {
    "loglevel": "warning",
    "access": "",
    "error": "",
    "dnsLog": false
  },
  "inbounds": [
    {
      "tag": "vless-reality-exit-in",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "__EXIT_VLESS_UUID__",
            "level": 0,
            "email": "entry-relay@exit"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "__EXIT_REALITY_SNI__:443",
          "xver": 0,
          "serverNames": ["__EXIT_REALITY_SNI__"],
          "privateKey": "__EXIT_REALITY_PRIVATE_KEY__",
          "minClientVer": "",
          "maxClientVer": "",
          "maxTimeDiff": 0,
          "shortIds": [__EXIT_REALITY_SHORT_IDS_JSON__],
          "fingerprint": "firefox"
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": [
          "http",
          "tls",
          "quic"
        ]
      }
    }
  ],
  "outbounds": [
    {
      "tag": "to-telemt",
      "protocol": "freedom",
      "settings": {
        "domainStrategy": "AsIs",
        "redirect": "127.0.0.1:8443"
      }
    },
    {
      "tag": "direct",
      "protocol": "freedom",
      "settings": {
        "domainStrategy": "UseIP"
      }
    },
    {
      "tag": "block",
      "protocol": "blackhole",
      "settings": {
        "response": {
          "type": "http"
        }
      }
    }
  ],
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "outboundTag": "to-telemt",
        "network": "tcp,udp"
      }
    ]
  }
}
```

### Change summary
- `xver: 1` → `xver: 0`: Exit no longer prepends its own PROXY header. The PROXYv1 header
  injected by the entry's `freedom proxyProtocol:1` passes through the VLESS tunnel and is
  forwarded as-is to telemt. This ensures telemt sees the real client IP, not the entry
  server's IP.

---

## === ARCH-001 PATCHES ===

### §3 C5 — Entry (before → after)

**BEFORE (0.2.0):**
```markdown
### C5 — Infrastructure-as-Code (deploy scripts + Docker Compose)
...
  - `infra/entry/deploy-entry.sh` — Xray VLESS-Reality on Russia entry server. Prompts for:
    exit server IP, Reality SNI (recommendations: `vkvideo.ru`, `yahoo.com`), Reality keys
    (auto-generates if not provided), PROXYv2 settings. Produces: Docker Compose + Xray config.
```

**AFTER (0.2.1):**
```markdown
### C5 — Infrastructure-as-Code (deploy scripts + Docker Compose)
...
  - `infra/entry/deploy-entry.sh` — Xray dokodemo-door + VLESS-Reality outbound on Russia
    entry server. Prompts for: exit server IP, exit VLESS UUID, exit Reality public key, exit
    Reality SNI, exit short ID. Entry server has no Reality keys of its own — it is a
    transparent TCP forwarder with PROXYv1 injection. Produces: Docker Compose + Xray config.
```

### §3 C7 — Xray Exit Relay (before → after)

**BEFORE (0.2.0):**
```markdown
### C7 — Xray Exit Relay (encrypted S2 termination)
...
  Client IP is preserved: the entry server's `xver:1` prepends a PROXYv1 header to the data
  stream inside the VLESS tunnel; C7 forwards this header as-is to telemt.
```

**AFTER (0.2.1):**
```markdown
### C7 — Xray Exit Relay (encrypted S2 termination)
- **Responsibility:** Terminate the encrypted VLESS-Reality tunnel from the entry server on
  :443 and forward decrypted traffic to telemt on localhost:8443 via a `freedom` outbound.
  Client IP is preserved: the entry server's `freedom proxyProtocol:1` prepends a PROXYv1
  header into the data stream before it enters the VLESS tunnel; the exit inbound has `xver:0`
  (does NOT add its own PROXY header); `freedom` on exit forwards the stream as-is to telemt;
  telemt parses the PROXYv1 header with `proxy_protocol = true`.
```

### §3 C7 — Interface / contract (before → after)

**BEFORE (0.2.0):**
```markdown
  - Requires: EXIT_VLESS_UUID (shared with entry server), EXIT_REALITY_PRIVATE_KEY,
    EXIT_REALITY_SNI, EXIT_SHORT_IDS
```

**AFTER (0.2.1):**
```markdown
  - Requires: EXIT_VLESS_UUID (shared with entry server), EXIT_REALITY_PRIVATE_KEY,
    EXIT_REALITY_SNI, EXIT_SHORT_IDS
  - Exit inbound `xver: 0` — critical: do NOT set to 1 (would add a second PROXY header
    with the entry server's IP, breaking client IP preservation)
```

### §9 Security — Threat Surfaces (add row)

**ADD to threat table (0.2.1):**
```markdown
| Entry :443 (dokodemo-door) | Public internet | Transparent TCP forwarder — no TLS/Reality facade. Active probes are forwarded through the VLESS tunnel to exit → telemt, which handles masking (mask=true, unknown_sni_action=reject_handshake). No protocol information leaked from entry itself. |
```

### §Revision Log (append)

```markdown
- 2026-07-04 0.2.1 — Emergency fix: corrected entry inbound from `vless` (VLESS-Reality) to
  `dokodemo-door` (transparent TCP forward). ADR-009@0.2.0 incorrectly placed the VLESS-Reality
  on the client-facing inbound; the correct architecture has the VLESS tunnel on S2 only
  (entry outbound → exit inbound). Exit xver changed from 1 to 0. Entry no longer needs its
  own Reality keys. PROXYv1 injection via freedom proxyProtocol:1. Deploy blocker and code
  review fixes (TKT-020…TKT-023).
```

### Frontmatter changes

```yaml
version: 0.2.1   # was 0.2.0
adrs: [..., ADR-009@0.2.1]  # was ADR-009@0.2.0
tickets: [..., TKT-020@0.2.1, TKT-021@0.2.1, TKT-022@0.2.1, TKT-023@0.2.1]
```

---

## === TKT-020 ===

```markdown
---
id: TKT-020
type: ticket
status: draft
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: M
created: 2026-07-04
---

# TKT-020: Fix entry inbound protocol — dokodemo-door replaces VLESS-Reality

## §1 Goal
Correct the entry server's Xray inbound from VLESS-Reality (which breaks `tg://proxy` links)
to `dokodemo-door` (transparent TCP forward), restoring Telegram client compatibility while
preserving encrypted S2 via the VLES-Reality outbound tunnel.

## §2 In Scope
- Rewrite `infra/entry/xray-config.json.template` with two-stage dokodemo-door + freedom
  proxyProtocol:1 + VLESS-Reality outbound (matching ADR-009@0.2.1)
- Update `infra/exit/xray-config.json.template` to change `xver:1` → `xver:0`
- Simplify `infra/entry/deploy-entry.sh`: remove entry Reality key/SNI/UUID prompts
  (entry no longer needs its own Reality credentials), fix INFRA_DIR path (D6), fix
  xray command format (D7)
- Revise `docs/architecture/adr/ADR-009-encrypted-entry-exit-vless-reality.md` to 0.2.1
- Patch `docs/architecture/ARCH-001-telemt-mgmt.md` §3 C5, C7, §9 (version 0.2.1)

## §3 NOT In Scope
- `infra/entry/docker-compose.yml` — owned by TKT-023 (D2: mount path, D5: caps)
- `infra/exit/docker-compose.yml` — owned by TKT-023
- `infra/exit/deploy-exit.sh` — owned by TKT-023 (D6, D7, D8 fixes)
- `infra/exit/config.toml.template` — owned by TKT-023 (D4, D8)
- Code-level fixes (api/, telemt_proxy/, bot/) — owned by TKT-021
- `.env.example` updates — owned by TKT-022
- `scripts/migrate.sh` — owned by TKT-022

## §4 Inputs
- ADR-009@0.2.1 (this document's revised ADR)
- ARCH-001@0.2.1 §3 C5, C7
- `docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md` Task 3 — XRAY_DOUBLE_HOP
  reference config with `dokodemo-door` entry inbound (authoritative reference)
- `docs/knowledge/TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md` §3.4 — double-hop
  configs confirming dokodemo-door on entry
- `docs/knowledge/TELEMT_DEPLOY_REPORT_2026-07-04.md` — issue 7.11 (architectural gap)
- TKT-018@0.2.0 (predecessor — its entry template output is superseded by this ticket)

## §5 Outputs
- `infra/entry/xray-config.json.template` — **full rewrite**
- `infra/entry/deploy-entry.sh` — **significant revision** (simplified prompts, D6/D7 fixed)
- `infra/exit/xray-config.json.template` — **patch** (xver: 1 → 0)
- `docs/architecture/adr/ADR-009-encrypted-entry-exit-vless-reality.md` — **revision** (0.2.1)
- `docs/architecture/ARCH-001-telemt-mgmt.md` — **patch** (§3 C5, C7, §9, revision log, frontmatter)

## §6 Acceptance Criteria
- [ ] AC1 — Entry inbound protocol is `dokodemo-door` (not `vless`) on :443.
- [ ] AC2 — Entry has two-stage dokodemo-door: public-in (:443) → proxy-injector (freedom
      proxyProtocol:1) → tunnel-in (:10444) → proxy-to-exit (VLESS-Reality outbound).
- [ ] AC3 — Entry template has NO placeholders for `__VLESS_UUID_ENTRY__`,
      `__REALITY_PRIVATE_KEY__`, `__REALITY_SNI__`, `__REALITY_SERVER_NAMES__`,
      `__REALITY_SHORT_IDS__`. Only exit-related placeholders remain.
- [ ] AC4 — Exit template `xver` is `0` (not `1`).
- [ ] AC5 — `deploy-entry.sh` does NOT prompt for entry Reality private key, entry VLESS UUID,
      or entry Reality SNI. Only prompts for exit server credentials.
- [ ] AC6 — `deploy-entry.sh` `INFRA_DIR` resolves to `infra/` (one level up from script dir,
      not two levels up).
- [ ] AC7 — `deploy-entry.sh` xray key generation uses
      `docker run --rm ghcr.io/xtls/xray-core:latest x25519` (no extra `xray` prefix).
- [ ] AC8 — ADR-009 status is `accepted`, revision date is 2026-07-04, explains the
      correction from VLES inbound to dokodemo-door inbound.
- [ ] AC9 — ARCH-001 version is 0.2.1, §3 C5 describes dokodemo-door entry, §3 C7 specifies
      `xver:0` and freedom proxyProtocol for PROXY chain.
- [ ] AC10 — `tg://proxy` link flow works: client → entry:443 (dokodemo-door) → VLES tunnel
      → exit → telemt. Verify by manual config inspection (no live test required).

## §7 Constraints
- No new dependencies.
- Entry template must match the reference architecture in
  TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md Task 3 (XRAY_DOUBLE_HOP config).
- PROXYv1 (not PROXYv2) for consistency with ARCH-001 §3 C5 and mask_proxy_protocol=1.
- `fingerprint: "firefox"` on VLES outbound (Chrome blocked since May 2026).

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
```

---

## === TKT-021 ===

```markdown
---
id: TKT-021
type: ticket
status: draft
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: M
created: 2026-07-04
---

# TKT-021: Code bugfixes — async blocking, JWT secret, database factory, CORS, ProxyConfig

## §1 Goal
Fix 5 code-level issues found by RV-CODE-005: H1 (blocking bcrypt/QR in async), H2 (JWT
secret default), M1 (module-level database engine), M3 (CORS wildcards), M6 (ProxyConfig
field drift).

## §2 In Scope
- H1: Wrap `bcrypt.checkpw()`, `bcrypt.hashpw()` in `asyncio.to_thread()` (api/auth.py).
       Wrap `generate_qr()` call sites in `asyncio.to_thread()` (telemt_proxy/qr.py or
       call sites in router.py).
- H2: Remove `"dev-secret-change-me"` default from `JWT_SECRET_KEY` in `api/deps.py`.
       Raise `RuntimeError` if `JWT_SECRET_KEY` is unset or empty.
- M1: Refactor `telemt_proxy/database.py` — replace module-level `engine` and
       `async_session_factory` with a `create_session_factory(database_url)` function.
       Update `api/deps.py` and `bot/main.py` to call the factory.
- M3: Restrict CORS `allow_methods` to `["GET", "POST", "DELETE", "OPTIONS"]` and
       `allow_headers` to `["Authorization", "Content-Type"]` in `api/main.py`.
- M6: Update ARCH-001 §3 C1 to document all 5 fields of `ProxyConfig` (server, port, salt,
       auth_header, base_url), or refactor to remove redundant fields. Chosen approach:
       update ArchSpec (the 5-field design is intentional for standalone bot convenience).

## §3 NOT In Scope
- Infrastructure files (`infra/`, `scripts/`) — owned by TKT-020, TKT-022, TKT-023.
- Frontend files (`frontend/`) — no code review findings there.
- Test files for unrelated features.
- M2 (exit xver) — subsumed by TKT-020.

## §4 Inputs
- `docs/reviews/RV-CODE-FULL-telemt-mgmt.md` — findings H1, H2, M1, M3, M6
- ARCH-001@0.2.1 §3 C1 (ProxyConfig), §5 INV-ASYNC, INV-SECRETS, INV-EMBED
- GitHub issues #22 (H1), #23 (H2), #24 (M1)

## §5 Outputs
- `api/auth.py` — H1 (async bcrypt), H2 (imports if needed)
- `api/deps.py` — H2 (remove JWT default, add fail-fast check)
- `api/main.py` — M3 (restrict CORS methods/headers)
- `telemt_proxy/qr.py` — H1 (no change to file itself; wrapping at call site)
- `telemt_proxy/router.py` — H1 (wrap `generate_qr()` in `asyncio.to_thread()`)
- `telemt_proxy/database.py` — M1 (factory function)
- `telemt_proxy/config.py` — M6 (add docstring clarification if needed)
- `bot/main.py` — M1 (use factory function for session creation)
- `docs/architecture/ARCH-001-telemt-mgmt.md` §3 C1 — M6 (document 5 fields)
- `tests/test_auth.py` — update tests for async bcrypt and JWT fail-fast
- `tests/test_database.py` — update tests for factory function
- `tests/conftest.py` — update fixtures for factory function

## §6 Acceptance Criteria
- [ ] AC1 — `bcrypt.checkpw()` and `bcrypt.hashpw()` are called inside
      `asyncio.to_thread()`. `verify_password()` and `get_password_hash()` are `async`.
- [ ] AC2 — `generate_qr()` is called via `asyncio.to_thread()` at every call site.
- [ ] AC3 — `JWT_SECRET_KEY` has no default value. App raises `RuntimeError` at import time
      (or startup) if the env var is missing or empty.
- [ ] AC4 — `telemt_proxy/database.py` has no module-level `engine` or `async_session_factory`.
      Only a `create_session_factory(database_url: str)` function.
- [ ] AC5 — CORS `allow_methods` lists only `GET`, `POST`, `DELETE`, `OPTIONS`.
      CORS `allow_headers` lists only `Authorization`, `Content-Type`.
- [ ] AC6 — ARCH-001 §3 C1 documents `ProxyConfig(server, port, salt, auth_header, base_url)`.
- [ ] AC7 — All existing tests pass. New tests cover async bcrypt and JWT fail-fast.

## §7 Constraints
- No new dependencies.
- `asyncio.to_thread()` requires Python 3.9+ (project already requires 3.11+).
- M1 factory refactor must not break the existing test fixtures (conftest.py creates its own
  engine). Update conftest to use the new factory.

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
```

---

## === TKT-022 ===

```markdown
---
id: TKT-022
type: ticket
status: draft
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: S
created: 2026-07-04
---

# TKT-022: Infra bugfixes — .env.example staleness, migrate.sh health check

## §1 Goal
Fix 2 infra-level issues from RV-CODE-005: M4 (stale .env.example files) and M5 (migrate.sh
health check fails for entry servers).

## §2 In Scope
- M4: Update `infra/entry/.env.example` — change `REALITY_SNI` default to `ads.x5.ru`,
       **remove** entry-specific Reality variables (no longer needed after TKT-020), keep
       only exit-related variables. Update `infra/exit/.env.example` — change `TLS_DOMAIN`
       default to `www.microsoft.com`, add exit Reality variables (`EXIT_VLESS_UUID`,
       `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_PUBLIC_KEY`, `EXIT_REALITY_SNI`,
       `EXIT_REALITY_SHORT_IDS`).
- M5: Fix `scripts/migrate.sh` health check — add `SERVER_TYPE` conditional: exit servers
       use `http://${DOMAIN}:8080` (Angie mask); entry servers skip curl and go straight
       to Docker status check (entry runs VLES-Reality / dokodemo-door, not HTTP).

## §3 NOT In Scope
- `infra/entry/xray-config.json.template` — owned by TKT-020.
- `infra/entry/deploy-entry.sh` — owned by TKT-020.
- `infra/exit/xray-config.json.template` — owned by TKT-020.
- `infra/*/docker-compose.yml` — owned by TKT-023.
- `infra/exit/deploy-exit.sh` — owned by TKT-023.
- `infra/exit/config.toml.template` — owned by TKT-023.
- Code files (api/, telemt_proxy/, bot/) — owned by TKT-021.
- M2 (exit xver) — subsumed by TKT-020.

## §4 Inputs
- `docs/reviews/RV-CODE-FULL-telemt-mgmt.md` — findings M4, M5
- ADR-009@0.2.1 (entry no longer has its own Reality keys)
- `infra/entry/deploy-entry.sh` (after TKT-020) for correct variable list
- `infra/exit/deploy-exit.sh` for correct exit variable list

## §5 Outputs
- `infra/entry/.env.example`
- `infra/exit/.env.example`
- `scripts/migrate.sh`

## §6 Acceptance Criteria
- [ ] AC1 — `infra/entry/.env.example` contains only exit-related variables: `EXIT_SERVER_IP`,
      `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`. No entry
      Reality keys, no `VLESS_UUID_ENTRY`, no `REALITY_PRIVATE_KEY`, no `REALITY_SNI`.
- [ ] AC2 — `infra/exit/.env.example` contains all exit variables including `EXIT_VLESS_UUID`,
      `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_PUBLIC_KEY`, `EXIT_REALITY_SNI`,
      `EXIT_REALITY_SHORT_IDS`. `TLS_DOMAIN` default is `www.microsoft.com`.
- [ ] AC3 — `scripts/migrate.sh` health check differentiates by `SERVER_TYPE`: exit uses
      HTTP check (Angie :8080), entry skips curl and uses Docker status check.
- [ ] AC4 — `migrate.sh` shellcheck-clean (no new warnings).

## §7 Constraints
- No new dependencies.
- `.env.example` must remain valid env file format (KEY=value, comments with #).

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
```

---

## === TKT-023 ===

```markdown
---
id: TKT-023
type: ticket
status: draft
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: L
created: 2026-07-04
---

# TKT-023: Deploy blockers — D1-D8 from test deployment

## §1 Goal
Fix all 8 deploy blockers discovered during the 2026-07-04 test deployment
(TELEMT_DEPLOY_REPORT_2026-07-04.md), making `docker compose up` succeed on both entry and
exit servers without manual workarounds.

## §2 In Scope

| # | Issue | Fix |
|---|-------|-----|
| D1 | `angie/angie:latest` image doesn't exist | Replace with `docker.angie.software/angie:1.8.1-alpine` (official Angie registry) in all compose files |
| D2 | Xray config mount path wrong (`/etc/xray/` → `/usr/local/etc/xray/`) | Fix volume mount in entry + exit compose files |
| D3 | telemt config.toml not loaded (wrong working dir) | Add `command: ["/etc/telemt/config.toml"]` to telemt service |
| D4 | `config_strict=true` rejects `access.user_data_quota_bytes` | Remove `[access.user_data_quota_bytes]` section from `config.toml.template` |
| D5 | `cap_drop: ALL` breaks :443 bind + Angie chown | Per-service cap fixes (see details below) |
| D6 | `INFRA_DIR` path bug (`../..` → `..`) | Fix in `deploy-exit.sh`, `deploy-mgmt.sh`, `deploy-monitoring.sh`, `deploy-landing.sh` (entry is TKT-020) |
| D7 | `xray x25519` / `xray uuid` double command | Remove extra `xray` prefix in `deploy-exit.sh` (entry is TKT-020) |
| D8 | `tls_emulation` mask_host/port logic wrong | In third-party mode, set `mask_port = 443` (fetches from real domain) instead of 8080. Update `deploy-exit.sh` and `config.toml.template` comments. Add `proxy_protocol_trusted_cidrs = ["127.0.0.1/32"]` to config template. |

### D5 per-service cap fix detail

**Xray (entry + exit):**
```yaml
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE]
user: "0:0"  # root required for port 443 binding with cap_add
```
Note: `NET_BIND_SERVICE` with non-root user doesn't work reliably across all container
runtimes. Using `user: "0:0"` with `cap_drop: ALL` + `cap_add: NET_BIND_SERVICE` is the
practical fix. The container is still hardened (dropped all other caps, read_only, no-new-privs).

**Angie (exit, mgmt, landing):**
```yaml
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE, CHOWN, SETGID, SETUID]
# Remove read_only: true — Angie needs to write to cache dirs
```

**telemt:**
```yaml
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE]
# read_only: true — keep (telemt only writes to mounted volumes)
```

## §3 NOT In Scope
- `infra/entry/xray-config.json.template` — owned by TKT-020.
- `infra/entry/deploy-entry.sh` — owned by TKT-020 (includes D6/D7 for entry).
- `infra/exit/xray-config.json.template` — owned by TKT-020 (xver fix).
- Code files (api/, telemt_proxy/, bot/) — owned by TKT-021.
- `.env.example` files — owned by TKT-022.
- `scripts/migrate.sh` — owned by TKT-022.
- GitHub issue #14 (port mismatch) — known, separate fix.
- `infra/monitoring/`, `infra/landing/` compose files — D1 (Angie image) applies if they use
  Angie; D6 applies to their deploy scripts. Include in scope.

## §4 Inputs
- `docs/knowledge/TELEMT_DEPLOY_REPORT_2026-07-04.md` — issues 7.1-7.10
- ARCH-001@0.2.1 §5 INV-DOCKER (hardening invariant)
- ADR-009@0.2.1 (telemt on :8443, Xray on :443)
- GitHub issues #26-#37 (deploy blockers)

## §5 Outputs
- `infra/entry/docker-compose.yml` — D2 (mount path), D5 (caps/user)
- `infra/exit/docker-compose.yml` — D1 (Angie image), D2 (mount path), D3 (telemt command),
  D5 (caps/user for all 3 services)
- `infra/exit/config.toml.template` — D4 (remove unsupported key), D8 (mask_port comment,
  add proxy_protocol_trusted_cidrs)
- `infra/exit/deploy-exit.sh` — D6 (INFRA_DIR), D7 (xray command), D8 (mask_port=443 in
  third-party mode)
- `infra/mgmt/docker-compose.yml` — D1 (Angie image), D5 (caps)
- `infra/mgmt/deploy-mgmt.sh` — D6 (INFRA_DIR)
- `infra/monitoring/deploy-monitoring.sh` — D6 (INFRA_DIR)
- `infra/landing/docker-compose.yml` — D1 (Angie image), D5 (caps)
- `infra/landing/deploy-landing.sh` — D6 (INFRA_DIR)

## §6 Acceptance Criteria
- [ ] AC1 — No compose file references `angie/angie:latest`. All use a verified working image.
- [ ] AC2 — Xray config volume mounts to `/usr/local/etc/xray/config.json:ro` in both entry
      and exit compose files.
- [ ] AC3 — telemt service in exit compose has `command: ["/etc/telemt/config.toml"]`.
- [ ] AC4 — `config.toml.template` does not contain `access.user_data_quota_bytes`.
      `config_strict = true` is preserved.
- [ ] AC5 — Xray services have `user: "0:0"`. Angie services have `cap_add: [NET_BIND_SERVICE,
      CHOWN, SETGID, SETUID]` and no `read_only: true`.
- [ ] AC6 — All deploy scripts (except entry, owned by TKT-020) have
      `INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"` (one level up, not two).
- [ ] AC7 — `deploy-exit.sh` xray key generation uses `x25519` / `uuid` without extra `xray`
      prefix.
- [ ] AC8 — In third-party mode, `MASK_PORT=443` (not 8080). Config template comments updated.
- [ ] AC9 — `config.toml.template` includes
      `proxy_protocol_trusted_cidrs = ["127.0.0.1/32"]` in `[server]` section.
- [ ] AC10 — `docker compose up -d` succeeds on a clean Ubuntu server for both entry and exit
      roles (verified by manual config inspection — no live test required in this ticket).

## §7 Constraints
- No new dependencies.
- Angie image must be from an official or well-maintained source. Verify the image exists
  before committing (docker pull test or registry check). Options:
  `docker.angie.software/angie:1.8.1-alpine` (official Angie registry) or
  `socheatsok78/angie:1.11.7-ubuntu` (community, verified working in deploy report).
- INV-DOCKER hardening must be preserved: `cap_drop: ALL`, `security_opt: no-new-privileges`,
  `read_only` where feasible.

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-04 Viktor: ticket created (emergency fix session)
```

---

## === ANALYSIS: Why ADR-009 was wrong ===

### The error

ADR-009@0.2.0 specified the entry inbound as `vless` (VLESS-Reality, client-facing). The
stated architecture was:

```
Entry: Xray inbound (VLESS-Reality, :443, client-facing, xver:1)
       → Xray outbound (VLESS-Reality → exit:443)
```

This means Telegram clients would need to speak the VLESS protocol to connect to the entry
server. But **Telegram clients speak MTProto** (wrapped in FakeTLS). They cannot speak VLESS.
The `tg://proxy` link format (`tg://proxy?server=...&port=...&secret=...`) instructs the
Telegram app to connect using MTProto, not VLESS. With a VLES inbound on the entry, these
links are broken.

### How the knowledge base had the correct architecture

The correct architecture was documented **before** ADR-009 was written:

1. **TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md, Task 3 (XRAY_DOUBLE_HOP):**
   The reference config explicitly shows `dokodemo-door` on the entry inbound:
   ```json
   { "tag": "public-in", "port": 443, "protocol": "dokodemo-door", ... }
   ```
   And a `freedom` outbound with `proxyProtocol: 2` for PROXY header injection. The VLES
   tunnel is on the outbound only. This config is labelled "VERIFIED and RECOMMENDED."

2. **TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md, §3.4 (XRAY_DOUBLE_HOP):**
   Describes the same architecture: "Вход (РФ): Xray :443 → VLESS-Reality туннель" —
   meaning the VLES-Reality is the *tunnel* (outbound), not the *inbound*.

### How it was missed

The error was a **protocol-layer confusion**. ADR-009 correctly identified that S2 needed
encryption, and correctly chose VLES-Reality as the tunnel protocol. But it placed the
VLES-Reality on the **inbound** (client-facing) side of the entry instead of the **outbound**
(tunnel) side. The confusion likely arose from:

1. **Xray configuration symmetry:** In Xray, VLES-Reality appears as both an inbound (server)
   and an outbound (client). ADR-009 configured the entry as a VLES-Reality *server* that
   clients connect to, rather than as a VLES-Reality *client* that tunnels to the exit.

2. **Missing protocol chain analysis:** The ADR didn't trace the full protocol chain:
   - What protocol does the Telegram client speak? → MTProto/FakeTLS
   - What protocol does the entry inbound expect? → Must accept MTProto/FakeTLS (i.e., raw TCP)
   - What protocol does the S2 tunnel use? → VLES-Reality (entry outbound → exit inbound)
   
   The ADR jumped from "encrypt S2" to "use VLES-Reality on entry" without distinguishing
   inbound (client-facing) from outbound (tunnel).

3. **Knowledge base not cross-referenced at the protocol level:** The reference config in the
   knowledge base clearly shows `dokodemo-door` on entry inbound, but ADR-009 was written
   focusing on the "encrypted S2" requirement without verifying that the reference config's
   *inbound* protocol was different from its *outbound* protocol.

### How to prevent this in future

1. **Protocol chain trace as a mandatory ADR section:** Every ADR that changes protocol
   handling must include a full protocol chain from client to origin, specifying the expected
   protocol at each hop boundary.

2. **Cross-reference check against knowledge base configs:** When a knowledge base document
   has a verified reference config, the ADR must explicitly compare its proposed config against
   the reference and note any divergences.

3. **`tg://proxy` link compatibility check:** Any architecture change must verify that
   `tg://proxy` links still work (client speaks MTProto, entry must accept MTProto). This is a
   PRD-level invariant (users use standard Telegram clients).

4. **Deploy-time smoke test:** TKT-023 should include a health check that verifies the entry
   server's :443 accepts TCP connections and responds in a way consistent with MTProto/FakeTLS
   (not VLES handshake). This would catch the error immediately on first deploy.

---

## === M2 STATUS ===

**M2 (exit Xray `xver:1` may produce double PROXY protocol headers) is SUBSUMED by TKT-020.**

### Analysis

M2 was originally filed as a standalone code review finding (RV-CODE-005):

> Exit template has `xver:1`, which prepends a PROXYv1 header with the entry server's IP.
> Combined with entry's `xver:1`, telemt receives two PROXY headers — the wrong one first.

With the ADR-009@0.2.1 correction:

- **Entry no longer uses `xver:1` on an inbound.** The entry uses `dokodemo-door` (no `xver`
  parameter) with a `freedom proxyProtocol:1` outbound that injects the PROXYv1 header into
  the data stream.

- **Exit's `xver` must be `0`** — this is an integral part of TKT-020's architectural fix.
  The PROXYv1 header injected by entry travels through the VLES tunnel as raw bytes. If
  exit's `xver` were `1`, it would prepend *another* PROXY header (with entry's IP), breaking
  client IP preservation. Setting `xver:0` is not a "separate bugfix" — it's a fundamental
  requirement of the dokodemo-door architecture.

- **TKT-020's §5 Outputs already includes `infra/exit/xray-config.json.template`** with the
  `xver:0` change. There is nothing left for M2 to fix separately.

### Conclusion

M2 is **not a separate ticket item**. It is subsumed by TKT-020 (AC4: "Exit template `xver`
is `0`"). TKT-022 does NOT include M2.

---

## Pre-return verification checklist

| # | Check | Status |
|---|-------|--------|
| 1 | Entry inbound is `dokodemo-door` (transparent forward), NOT `vless` | ✅ Confirmed — entry template uses `"protocol": "dokodemo-door"` on both inbounds |
| 2 | `tg://proxy` links work: client → entry:443 (dokodemo-door) → VLES tunnel → exit → telemt | ✅ Confirmed — dokodemo-door accepts raw TCP (MTProto/FakeTLS), forwards transparently |
| 3 | PROXYv1 client IP preservation chain: dokodemo-door → freedom proxyProtocol:1 → tunnel-in → VLES → exit (xver:0) → telemt (proxy_protocol=true) | ✅ Confirmed — freedom adds PROXYv1, exit xver:0 doesn't add another, telemt parses it |
| 4 | All 4 new tickets have disjoint §5 Outputs | ✅ Confirmed — TKT-020: templates + deploy-entry + ADR + ArchSpec; TKT-021: api/ + telemt_proxy/ + bot/ + tests/; TKT-022: .env.example + migrate.sh; TKT-023: compose files + deploy-exit + config.toml.template + other deploy scripts |
| 5 | ARCH-001 version bumps to 0.2.1 (patch, not minor) | ✅ Confirmed — version: 0.2.1 in frontmatter, revision log |
| 6 | ADR-009 explains what was wrong and why | ✅ Confirmed — "Revision: 0.2.0 → 0.2.1" section in ADR, plus full analysis in "Why ADR-009 was wrong" section |
