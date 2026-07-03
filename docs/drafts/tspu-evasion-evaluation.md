# TSPU Evasion Evaluation — ARCH-001@0.1.2 → 0.2.0

**Date:** 2026-07-03
**Evaluator:** Technical Architect (Viktor)
**Scope:** 6 improvements from issue #15 + research addendum, evaluated against TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md and TELEMT_TSPU_EVASION_PATTERNS.md

---

## Executive Summary

**Version bump: 0.1.2 → 0.2.0 (minor)** — Improvement 5 (encrypted S2) is recommended; it adds a new component (C7: Xray exit relay) and changes the exit deploy topology.

| # | Improvement | Recommendation | Rationale |
|---|---|---|---|
| 1 | Russian Reality SNI | **IMPLEMENT** | Research §1 cross-validates `ads.x5.ru` in 6 production configs; `yahoo.com` triggers geographic anomaly |
| 2 | PROXYv1 instead of PROXYv2 | **IMPLEMENT** | Research §4 decision matrix rates PROXYv2 at 5/10 evasion vs PROXYv1 at 8/10; binary signature is trivially fingerprintable |
| 3 | Angie SNI routing template | **IMPLEMENT** | Patterns doc Pattern 4 validates production use; additive, no default behavior change |
| 4 | Russian datacenter recommendation | **IMPLEMENT** | Research §1 documents Selectel/Yandex.Cloud Signal 1 flagging; deploy guidance prevents operator misstep |
| 5 | Encrypted entry → exit (VLESS-Reality) | **IMPLEMENT** | Research §5 + §6 post-handshake payload analysis evidence; production systems unanimously encrypt S2 |
| 6 | Self-steal domain strategy | **IMPLEMENT** (optional) | Research §2 shows self-steal eliminates ASN mismatch by construction; `www.microsoft.com` as new default |

**New ADRs:** ADR-008, ADR-009, ADR-010
**New tickets:** TKT-014 through TKT-019
**New component:** C7 — Xray Exit Relay

---

## Improvement 1: Russian Reality SNI on Entry Server

### Evaluation

**Research evidence — convincing.**
TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 provides a top-10 candidate table with cross-validation data. `ads.x5.ru` (X5 Retail CDN) appears in the igareck/vpn-configs-for-russia WHITE-SNI-RU-all.txt whitelist with 6 occurrences (highest frequency of any single domain), and one production config explicitly tags it for Beeline mobile with IP `78.159.247.177`. The research rates it Tier 1: "Cross-validated in production configs; no blocking reports as of July 2026."

The current default `yahoo.com` fails the A-record cross-check: Yahoo resolves to Akamai/Verizon Media CDN with no Russian PoP. TSPU seeing SNI=yahoo.com from a Russian IP connecting to another Russian IP is a geographic anomaly (§1: "real Yahoo traffic from Russia routes through Yahoo's international PoPs, not server-to-server within Russia").

`ya.ru` (Yandex AS13238) is recommended as secondary — Xray community-recommended, Yandex core domain, confirmed Russian PoP. The research (§1 "Single vs Multiple serverNames") recommends 2–3 names from the same provider/ASN cluster for resilience, but warns against mixing providers (e.g., Yandex + VK in the same list).

Note: `ads.x5.ru` and `ya.ru` are different ASN clusters (X5 vs Yandex). The research warns against mixing ASNs in serverNames. However, the primary purpose of multiple serverNames is resilience against TLS config changes, not load distribution — and the probe surface is limited since Xray uses `serverNames[0]` for the active connection. **Recommendation: use `ads.x5.ru` as primary and sole serverName for safety.** If resilience is needed, add `ya.ru` only after confirming both resolve to Russian IPs from the entry server's perspective.

For the initial safe change, I'll template the serverNames to support multiple entries (same mechanism as shortIds), default to `ads.x5.ru` only, and document `ya.ru` as a tested secondary option.

**Architecture compatibility:** Config change only. No new component. ARCH-001@0.1.2 §3 C5 defines deploy-entry.sh as prompting for REALITY_SNI — we update the default and recommendation text.

**PRD compliance:** No Non-Goal violated. R12 says "Reality SNI chosen by operator at deploy time (recommendations: vkvideo.ru for Russian domestic whitelisted domain, yahoo.com as telemt default)" — updating the recommendation from yahoo.com to ads.x5.ru is consistent with the spirit of R12. The operator still chooses at deploy time.

**Invariants:** INV-IDEMPOTENT preserved (script prompts are unchanged in structure).

**Artefacts needed:** Ticket (config change). No ADR required (parameter-level change within existing component).

### Artefacts

#### Config diff: `infra/entry/xray-config.json.template`

**Old (inbound realitySettings):**
```json
          "dest": "__REALITY_SNI__:443",
          "xver": 0,
          "serverNames": [
            "__REALITY_SNI__"
          ],
```

**New:**
```json
          "dest": "__REALITY_SNI__:443",
          "xver": 0,
          "serverNames": [__REALITY_SERVER_NAMES__],
```

#### Config diff: `infra/entry/deploy-entry.sh`

**Old (REALITY_SNI prompt):**
```bash
# REALITY_SNI — recommended: vkvideo.ru (RU domestic), yahoo.com (telemt default).
REALITY_SNI="$(prompt_for "REALITY_SNI" \
    "Enter Reality SNI (recommend: vkvideo.ru for RU domestic, yahoo.com as default)" \
    "yahoo.com")"
save_env_var "$ENV_FILE" "REALITY_SNI" "$REALITY_SNI"
```

**New:**
```bash
# REALITY_SNI — recommended: ads.x5.ru (Russian CDN, TSPU-whitelisted, production-validated).
# See docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 for full candidate list.
# Secondary option: ya.ru (Yandex core domain). Do NOT mix ASN clusters in serverNames.
REALITY_SNI="$(prompt_for "REALITY_SNI" \
    "Enter Reality SNI (recommend: ads.x5.ru for RU domestic CDN, ya.ru as secondary)" \
    "ads.x5.ru")"
save_env_var "$ENV_FILE" "REALITY_SNI" "$REALITY_SNI"

# REALITY_SNI_SECONDARY — optional second serverName for resilience.
# Leave empty for single-SNI mode (safest). If set, must be same ASN cluster as primary.
REALITY_SNI_SECONDARY="$(prompt_for "REALITY_SNI_SECONDARY" \
    "Enter secondary Reality SNI (optional, press Enter to skip)" \
    "")"
save_env_var "$ENV_FILE" "REALITY_SNI_SECONDARY" "$REALITY_SNI_SECONDARY"
```

**Old (template substitution):**
```bash
sed \
    -e "s|__EXIT_SERVER_IP__|${EXIT_SERVER_IP}|g" \
    -e "s|__REALITY_SNI__|${REALITY_SNI}|g" \
    -e "s|__REALITY_PRIVATE_KEY__|${REALITY_PRIVATE_KEY}|g" \
    -e "s|__REALITY_SHORT_IDS__|${REALITY_SHORT_IDS_JSON}|g" \
    "$XRAY_TEMPLATE" > "$XRAY_CONFIG"
```

**New:**
```bash
# Build REALITY_SERVER_NAMES as JSON array body: "sni1" or "sni1", "sni2"
if [[ -n "$REALITY_SNI_SECONDARY" ]]; then
    REALITY_SERVER_NAMES_JSON="\"${REALITY_SNI}\", \"${REALITY_SNI_SECONDARY}\""
else
    REALITY_SERVER_NAMES_JSON="\"${REALITY_SNI}\""
fi

sed \
    -e "s|__EXIT_SERVER_IP__|${EXIT_SERVER_IP}|g" \
    -e "s|__REALITY_SNI__|${REALITY_SNI}|g" \
    -e "s|__REALITY_PRIVATE_KEY__|${REALITY_PRIVATE_KEY}|g" \
    -e "s|__REALITY_SHORT_IDS__|${REALITY_SHORT_IDS_JSON}|g" \
    -e "s|__REALITY_SERVER_NAMES__|${REALITY_SERVER_NAMES_JSON}|g" \
    "$XRAY_TEMPLATE" > "$XRAY_CONFIG"
```

**Old (success banner):**
```bash
echo "  Reality SNI:     $REALITY_SNI"
echo "  Listening:       0.0.0.0:443 (VLESS+Reality)"
echo "  PROXYv2:         enabled (real client IP → exit server)"
```

**New:**
```bash
echo "  Reality SNI:     $REALITY_SNI (primary)${REALITY_SNI_SECONDARY:+, $REALITY_SNI_SECONDARY (secondary)}"
echo "  Listening:       0.0.0.0:443 (VLESS+Reality)"
echo "  PROXYv1:         enabled (real client IP → exit server)"
```

#### Ticket: TKT-014

```markdown
---
id: TKT-014
type: ticket
status: draft
arch_ref: ARCH-001@0.2.0
depends_on: []
estimate: S
created: 2026-07-03
---

# TKT-014: Russian Reality SNI Defaults

## §1 Goal
Update the entry server Reality SNI default from `yahoo.com` to `ads.x5.ru` (Russian CDN, TSPU-whitelisted, production-validated) and support optional secondary serverNames.

## §2 In Scope
- Update `REALITY_SNI` default in `deploy-entry.sh` from `yahoo.com` to `ads.x5.ru`
- Add `REALITY_SNI_SECONDARY` prompt to `deploy-entry.sh`
- Update `xray-config.json.template` to use `__REALITY_SERVER_NAMES__` placeholder (JSON array body)
- Update template substitution logic in `deploy-entry.sh`
- Update success banner text

## §3 NOT In Scope
- Changing the `fingerprint` parameter (remains `firefox`)
- Modifying the `freedom` outbound section (handled by TKT-015)
- Exit server config changes
- Automated SNI validation against whitelist databases

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (top-10 candidates, validation data)
- TELEMT_TSPU_EVASION_PATTERNS.md Pattern 1

## §5 Outputs
- `infra/entry/xray-config.json.template` (inbound realitySettings section only)
- `infra/entry/deploy-entry.sh` (SNI prompt and substitution sections)

## §6 Acceptance Criteria
- [ ] AC1 — `deploy-entry.sh` default REALITY_SNI is `ads.x5.ru` (not `yahoo.com`)
- [ ] AC2 — `deploy-entry.sh` prompts for optional `REALITY_SNI_SECONDARY`
- [ ] AC3 — When REALITY_SNI_SECONDARY is empty, `serverNames` contains one entry: `["ads.x5.ru"]`
- [ ] AC4 — When REALITY_SNI_SECONDARY is set (e.g. `ya.ru`), `serverNames` contains two entries: `["ads.x5.ru", "ya.ru"]`
- [ ] AC5 — `dest` field uses primary SNI: `ads.x5.ru:443`
- [ ] AC6 — Template substitution produces valid JSON (verify with `jq .`)
- [ ] AC7 — Idempotent re-run: existing `.env` values are preserved (INV-IDEMPOTENT)

## §7 Constraints
- No new dependencies
- Must not modify the outbound section of `xray-config.json.template`

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
```

---

## Improvement 2: PROXYv1 Instead of PROXYv2

### Evaluation

**Research evidence — convincing.**
TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §4 provides a decision matrix rating PROXYv2 at 5/10 for TSPU evasion vs PROXYv1 at 8/10. The specific detection vector: PROXYv2 sends a 12-byte binary signature `\x0D\x0A\x0D\x0A\x00\x0D\x0A\x51\x55\x49\x54\x0A` as the first bytes of the TCP stream, before the TLS ClientHello. This is "trivially detectable by any DPI system doing a simple byte-string match on the first packet" (§4). PROXYv1 sends an ASCII line that "superficially resembles an HTTP header and is less distinctive" (§4).

telemt 3.4.22 confirmed compatible: §7 confirms `mask_proxy_protocol = 1` in `[censorship]` enables PROXYv1 outgoing, while `proxy_protocol = true` in `[server]` enables auto-detection of incoming PROXYv1/v2 headers (§4, references [10][11]). The `proxy_protocol` parameter is boolean and currently absent from the template — must be added (§4: "This parameter is not present in the default config.toml template and must be added manually [12]").

**Critical constraint:** When `proxy_protocol = true` is set, telemt rejects ALL connections without a PROXY header (§4, [13]). This is correct for the double-hop architecture where all traffic arrives from the entry server via Xray.

**Port fix:** The `redirect` field currently points to `__EXIT_SERVER_IP__:8443` but the exit server listens on `:443`. The task notes this as issue #14 and instructs to address the port fix alongside this improvement since both touch the same template line. Changing to `:443` fixes this.

**Architecture compatibility:** Config change on both entry and exit templates. No new component.

**PRD compliance:** R12 mentions "PROXYv2 forwarding to exit server" — changing to PROXYv1 modifies the implementation of real-client-IP preservation, but the goal (IP preservation) is unchanged. This is an implementation detail, not a PRD-level change.

**Invariants:** No violation. INV-DOCKER unaffected.

### Artefacts

#### Config diff: `infra/entry/xray-config.json.template`

**Old (outbound):**
```json
    {
      "tag": "proxy-to-exit",
      "protocol": "freedom",
      "settings": {
        "domainStrategy": "AsIs",
        "redirect": "__EXIT_SERVER_IP__:8443",
        "proxyProtocol": 2
      }
    },
```

**New:**
```json
    {
      "tag": "proxy-to-exit",
      "protocol": "freedom",
      "settings": {
        "domainStrategy": "AsIs",
        "redirect": "__EXIT_SERVER_IP__:443",
        "proxyProtocol": 1
      }
    },
```

#### Config diff: `infra/exit/config.toml.template`

**Old ([server] section):**
```toml
[server]
port = 443
# Prometheus metrics — bound to localhost, accessible via UFW-restricted port.
metrics_port = 9090
metrics_listen = "0.0.0.0:9090"
```

**New:**
```toml
[server]
port = 443
# Enable incoming PROXY protocol header parsing (v1 or v2 auto-detected).
# When true, telemt rejects connections without a PROXY header.
# Required for double-hop: all traffic arrives from entry server via Xray.
proxy_protocol = true
# Prometheus metrics — bound to localhost, accessible via UFW-restricted port.
metrics_port = 9090
metrics_listen = "0.0.0.0:9090"
```

**Old ([censorship] section):**
```toml
[censorship]
# FakeTLS domain — the SNI presented to DPI inspection.
tls_domain = "__TLS_DOMAIN__"
# mask = true: non-TLS requests are redirected to the mask host (Angie :8080).
mask = true
# unknown_sni_action: reject connections with unrecognised SNI (hardening).
unknown_sni_action = "reject_handshake"
```

**New:**
```toml
[censorship]
# FakeTLS domain — the SNI presented to DPI inspection.
tls_domain = "__TLS_DOMAIN__"
# tls_emulation: fetches real ServerHello from mask_host:mask_port for camouflage.
tls_emulation = true
# mask = true: non-TLS requests are redirected to the mask host (Angie :8080).
mask = true
# mask_proxy_protocol: version of PROXY header sent TO mask_host.
# 1 = PROXYv1 (text-based, less fingerprintable than binary PROXYv2).
mask_proxy_protocol = 1
# unknown_sni_action: reject connections with unrecognised SNI (hardening).
unknown_sni_action = "reject_handshake"
```

#### Ticket: TKT-015

```markdown
---
id: TKT-015
type: ticket
status: draft
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-014]
estimate: S
created: 2026-07-03
---

# TKT-015: PROXYv1 Protocol and Exit PROXY Config

## §1 Goal
Switch entry→exit PROXY protocol from v2 (binary, fingerprintable) to v1 (text-based) and add explicit PROXY protocol configuration to the exit server config template.

## §2 In Scope
- Change `proxyProtocol` from `2` to `1` in entry `xray-config.json.template` outbound
- Fix `redirect` port from `:8443` to `:443` in entry template (issue #14 port mismatch)
- Add `proxy_protocol = true` to exit `config.toml.template` `[server]` section
- Add `mask_proxy_protocol = 1` to exit `config.toml.template` `[censorship]` section
- Add `tls_emulation = true` to exit `config.toml.template` `[censorship]` section

## §3 NOT In Scope
- Entry inbound changes (handled by TKT-014)
- Self-steal domain configuration (handled by TKT-019)
- Encrypted S2 architecture changes (handled by TKT-018)
- PROXYv1 compatibility testing against telemt (documented compatible in §7 of research)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §4 (decision matrix, telemt 3.4.22 compat)
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §7 (PROXYv1 support confirmation)

## §5 Outputs
- `infra/entry/xray-config.json.template` (outbound section only)
- `infra/exit/config.toml.template` (`[server]` and `[censorship]` sections)

## §6 Acceptance Criteria
- [ ] AC1 — Entry template outbound `proxyProtocol` is `1` (not `2`)
- [ ] AC2 — Entry template outbound `redirect` port is `:443` (not `:8443`)
- [ ] AC3 — Exit template `[server]` section contains `proxy_protocol = true`
- [ ] AC4 — Exit template `[censorship]` section contains `mask_proxy_protocol = 1`
- [ ] AC5 — Exit template `[censorship]` section contains `tls_emulation = true`
- [ ] AC6 — Generated entry config is valid JSON (`jq .` passes)
- [ ] AC7 — Generated exit config is valid TOML

## §7 Constraints
- telemt 3.4.22+ required (PROXYv1 support via mask_proxy_protocol)
- No new dependencies

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
```

---

## Improvement 3: Angie SNI Routing Template for Shared Exit Servers

### Evaluation

**Research evidence — convincing.**
TELEMT_TSPU_EVASION_PATTERNS.md Pattern 4 documents production infrastructure "routinely" running multiple proxy protocols on a single server using Angie SNI stream routing. The architecture is clear: Angie reads the SNI field from the TLS ClientHello (no decryption, no certificate handling) and routes the raw TCP stream to the appropriate backend. The pattern provides a concrete config example with `ssl_preread on`.

**Architecture compatibility:** Fully compatible. This is an additive optional template — the current standalone template (telemt owns :443) remains the default. The new template is for operators who co-locate telemt with other services on the same server (cost optimization, as noted in the patterns doc).

**PRD compliance:** No Non-Goal violated. R8 says Docker Compose files are "self-contained and independently deployable" — the SNI routing template adds a deployment variant, not a mandatory change.

**Invariants:** INV-DOCKER applies — the Angie SNI router container must follow the same hardening pattern (cap_drop ALL, read_only, security_opt). INV-IDEMPOTENT applies to any deploy script changes.

**Note:** If Improvement 5 (encrypted S2) is also adopted, the SNI routing template must account for Xray on :443 instead of telemt. The template should route by SNI to either Xray (for encrypted S2 traffic) or other services. I'll provide the template in a way that works with both architectures.

### Artefacts

#### ADR-008: Angie SNI Routing for Shared Exit Servers

```markdown
---
id: ADR-008
type: adr
status: proposed
created: 2026-07-03
---

# ADR-008: Angie SNI Routing for Shared Exit Servers

## Context
ARCH-001@0.2.0 §3 C5 deploys telemt with exclusive ownership of port 443 on the exit server. Operators who co-locate telemt with other TLS-based services (e.g., a web server, another proxy instance) face port conflicts. TELEMT_TSPU_EVASION_PATTERNS.md Pattern 4 documents production infrastructure using Angie SNI stream routing to share port 443 across multiple services.

## Decision
We will add an optional `infra/exit/angie-sni-router.conf.template` that implements Angie `stream` module SNI routing on port 443. This template:
- Reads the SNI from the TLS ClientHello via `ssl_preread` (no decryption, no certificate handling)
- Routes by SNI to backend services on internal ports (e.g., telemt on :8443, other service on :8445)
- Is provided as an alternative to the default standalone deployment; the default remains unchanged
- Works with both the `freedom`-based and encrypted-S2 architectures

## Consequences
- **Positive:** Operators can share a single exit server IP across multiple TLS services, reducing cost.
- **Positive:** telemt moves to an internal port (:8443), not directly exposed — defense in depth.
- **Negative / cost:** Additional Angie configuration complexity; operators must understand SNI routing.
- **Follow-ups:** Documentation must clearly distinguish "standalone" (telemt on :443) from "shared" (Angie SNI routing on :443) deployment modes.

## Alternatives considered
- **HAProxy SNI routing** — rejected; Angie is already in the stack (C5 exit uses Angie for mask_host). Adding HAProxy introduces a new dependency.
- **Xray fallback routing** — rejected for the non-encrypted-S2 case; fallback configuration is complex and Xray-specific. For the encrypted S2 case, Xray is already on :443 and can be combined with Angie SNI routing if needed.
```

#### New file: `infra/exit/angie-sni-router.conf.template`

```nginx
# ─────────────────────────────────────────────────────────────────────────────
# angie-sni-router.conf.template — Optional SNI-based TCP routing on :443.
#
# Use this template when co-locating telemt with other TLS services on a
# shared exit server.  Angie reads the SNI from the TLS ClientHello
# (ssl_preread, no decryption) and routes the raw TCP stream to the
# appropriate backend on an internal port.
#
# Default mode (without this template): telemt owns :443 exclusively.
# Shared mode (with this template):     Angie owns :443, routes by SNI.
#
# Backends (adjust ports and SNI mappings to your setup):
#   __TELEMT_SNI__   → 127.0.0.1:8443   (telemt or Xray-exit)
#   default          → 127.0.0.1:8443   (fallback to telemt)
#
# Per ARCH-001@0.2.0 §3 C5 / ADR-008.
# ─────────────────────────────────────────────────────────────────────────────

worker_processes auto;

events {
    worker_connections 1024;
}

# ── SNI-based TCP stream routing (no TLS termination) ────────────────────────
stream {
    # Map SNI hostname → backend address
    map $ssl_preread_server_name $backend {
        __TELEMT_SNI__    127.0.0.1:8443;
        default           127.0.0.1:8443;
    }

    # Listen on :443, read SNI, proxy raw TCP to backend
    server {
        listen 443;
        listen [::]:443;

        ssl_preread on;
        proxy_pass $backend;

        # Preserve client IP via PROXY protocol to backend (optional).
        # Enable only if the backend supports PROXY protocol.
        # proxy_protocol on;
    }
}

# ── HTTP block for mask host (unchanged from default) ────────────────────────
http {
    include       /etc/angie/mime.types;
    default_type  application/octet-stream;

    sendfile    on;
    tcp_nopush  on;
    keepalive_timeout 65;

    server {
        listen 8080;
        listen [::]:8080;
        server_name _;

        root /var/www/mask;
        index index.html;

        location / {
            try_files $uri $uri/ =404;
        }
    }
}
```

#### Ticket: TKT-016

```markdown
---
id: TKT-016
type: ticket
status: draft
arch_ref: ARCH-001@0.2.0
depends_on: []
estimate: M
created: 2026-07-03
---

# TKT-016: Angie SNI Routing Template for Shared Exit Servers

## §1 Goal
Add an optional Angie SNI routing template that enables co-locating telemt with other TLS services on a shared exit server using stream-level SNI routing on port 443.

## §2 In Scope
- Create `infra/exit/angie-sni-router.conf.template` with Angie stream SNI routing
- Add `__TELEMT_SNI__` placeholder for operator's telemt SNI domain
- Include inline documentation explaining standalone vs shared mode
- Add a section to README.md documenting the shared-server deployment option

## §3 NOT In Scope
- Changing the default standalone deployment (telemt on :443 remains default)
- Modifying `deploy-exit.sh` to auto-detect shared mode (operator manually selects template)
- Docker Compose changes for the shared-server variant (operator adapts manually)
- Xray SNI routing (Xray has its own fallback mechanism; this template uses Angie)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- ADR-008
- TELEMT_TSPU_EVASION_PATTERNS.md Pattern 4

## §5 Outputs
- `infra/exit/angie-sni-router.conf.template` (new file)
- `README.md` (shared-server deployment section)

## §6 Acceptance Criteria
- [ ] AC1 — `angie-sni-router.conf.template` exists and contains `ssl_preread on` in a `stream` block
- [ ] AC2 — Template uses `__TELEMT_SNI__` placeholder for the telemt service SNI
- [ ] AC3 — Template routes default (unknown SNI) to telemt backend
- [ ] AC4 — Template includes the `http` block for mask host on :8080 (preserving existing mask_host functionality)
- [ ] AC5 — README.md documents standalone vs shared deployment modes with a clear comparison table
- [ ] AC6 — Template validates as syntactically correct Angie config (angie -t)

## §7 Constraints
- No new dependencies (Angie is already in the stack)
- Must not modify existing `angie.conf.template` (the default standalone template)

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
```

---

## Improvement 4: Russian Datacenter Recommendation for Entry

### Evaluation

**Research evidence — convincing.**
TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 documents the June 2026 "Siberian" behavioral module (§6) with three-signal AND detection: Signal 1 is "Suspicious server subnet" with Selectel and Yandex.Cloud *specifically confirmed* as flagged ASNs. §3 explicitly states: "If your entry server is on Selectel, this means Signal 1 is always active for your connections regardless of SNI choice."

The mitigation is clear (§3): "move entry server to a non-flagged RU provider (Beget, TimeWeb, reg.ru), or accept that evasion depends on keeping Signals 2 and 3 clean."

TELEMT_TSPU_EVASION_PATTERNS.md Pattern 5 corroborates with a provider table showing Beget and Selectel at "Low" filtering intensity — but this pre-dates the June 2026 Siberian module that specifically flags Selectel subnets. The newer research supersedes the patterns doc on this specific point.

**Architecture compatibility:** Docs-only change. No config modification, no new component.

**PRD compliance:** No Non-Goal violated. §7 Constraints mentions "cheap RU VPS (1vCPU/1GB) for entry server" without specifying provider — adding provider guidance is consistent.

**Artefacts needed:** Ticket (docs change). No ADR required.

### Artefacts

#### Config diff: `infra/entry/deploy-entry.sh`

**Old (banner block):**
```bash
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  telemt-mgmt — Entry Server Deploy (Xray VLESS-Reality)      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
```

**New:**
```bash
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  telemt-mgmt — Entry Server Deploy (Xray VLESS-Reality)      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  ⚠  RU datacenter guidance (July 2026):"
echo "     Recommended: Beget, TimeWeb, reg.ru (non-flagged ASNs)"
echo "     Caution:     Selectel, Yandex.Cloud — subnet flagged by"
echo "                  June 2026 TSPU Siberian module (Signal 1)."
echo "     See: docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1, §6"
echo ""
```

#### Ticket: TKT-017

```markdown
---
id: TKT-017
type: ticket
status: draft
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-014]
estimate: S
created: 2026-07-03
---

# TKT-017: Russian Datacenter Provider Guidance

## §1 Goal
Add Russian datacenter provider recommendations and warnings to the entry server deploy script and README, documenting the June 2026 TSPU Siberian module's subnet flagging of Selectel and Yandex.Cloud.

## §2 In Scope
- Add provider guidance banner to `deploy-entry.sh` (Beget/TimeWeb/reg.ru recommended; Selectel/Yandex.Cloud warning)
- Add a "Russian Entry Server Provider Selection" section to README.md
- Reference TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 and §6

## §3 NOT In Scope
- Automated provider detection or IP-to-ASN lookup in the deploy script
- Exit server provider guidance (exit is EU-based; no TSPU subnet flagging applies)
- Modifying deploy-entry.sh functional logic (banner text only)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (Selectel/Yandex.Cloud flag note), §3 (path-dependent matrix), §6 (Siberian module)

## §5 Outputs
- `infra/entry/deploy-entry.sh` (banner text block only)
- `README.md` (provider selection section)

## §6 Acceptance Criteria
- [ ] AC1 — `deploy-entry.sh` displays provider guidance before prompts
- [ ] AC2 — Beget, TimeWeb, reg.ru explicitly recommended
- [ ] AC3 — Selectel, Yandex.Cloud explicitly warned as Signal-1 flagged
- [ ] AC4 — README.md contains a provider comparison table with Signal 1 status
- [ ] AC5 — Documentation references TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 and §6

## §7 Constraints
- Text changes only; no functional script modifications

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
```

---

## Improvement 5: Encrypted Entry → Exit Segment (VLESS-Reality)

### Evaluation

**Research evidence — convincing and urgent.**
TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 makes the strongest case in the entire research corpus: "TSPU at the RU→EU international gateway sees: (1) the FakeTLS ClientHello with the `tls_domain` SNI, (2) the ServerHello characteristics, and (3) post-handshake MTProto payload patterns." §6 confirms post-handshake payload analysis as a documented, active TSPU capability: "TSPU detects MTProto traffic inside FakeTLS based on payload analysis after the TLS connection is established. This is a documented capability separate from handshake fingerprinting."

§5 states: "Production systems with Russian DC entry servers use encrypted S2." The TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3 corroborates: "Production infrastructure **never** sends raw proxy traffic on the RU → EU segment."

The June 2026 detection waves (§6) targeted exactly the traffic that `freedom` exposes: MTProto patterns on international links. Federal operators (MTS, YOTA) showed 0% success rate in May 2026 testing (PRD §7). Encrypting S2 makes the international gateway see only a VLESS-Reality handshake — "indistinguishable from a legitimate HTTPS connection" (§5).

**Latency impact:** §5 estimates 1–3 RTT additional overhead for connection setup (80–240 ms for RU→EU 40–80 ms RTT), paid once per persistent connection. One source estimates 15–25 ms sustained throughput overhead for XHTTP-based transport. "Acceptable for Telegram messaging use" (§5).

**Is this overkill?** No. The research answers this directly (§5): "If your current freedom-based deployment passes TSPU without issues, encrypting S2 is a defensive measure against future capability upgrades... the June 2026 detection evolution shows TSPU is actively expanding its international gateway inspection capabilities." Given federal operators at 0% success and post-handshake payload analysis confirmed active, this is the single most impactful improvement.

**Architecture compatibility:** This is an architecture-level change. It adds a new component (C7: Xray on exit server for VLESS-Reality termination) and changes the deploy topology:
- Current: Entry Xray → freedom (raw TCP) → exit telemt:443
- New: Entry Xray → VLESS-Reality → exit Xray:443 → freedom → exit telemt:8443

Port conflict resolution (§5, §7): telemt moves from :443 to :8443 (internal, not externally exposed). Xray owns :443 for the VLESS-Reality inbound from the entry server. Exit docker-compose switches to host network mode (matching entry server pattern) so Xray can reach telemt on localhost:8443.

**PRD compliance:** No Non-Goal violated. R7 says `deploy-exit.sh` deploys "Telemt + Angie mask host on EU exit server" — adding Xray to the exit server extends the deploy target but doesn't violate the one-deploy-script-per-target model. R8 says Docker Compose files are "self-contained and independently deployable" — the updated docker-compose remains self-contained.

**Invariants check:**
- INV-DOCKER: New Xray container follows hardening pattern (cap_drop ALL, read_only, NET_BIND_SERVICE, no-new-privileges) ✓
- INV-SECRETS: New secrets (EXIT_VLESS_UUID, EXIT_REALITY_PRIVATE_KEY) stored in .env ✓
- INV-IDEMPOTENT: deploy-exit.sh handles new prompts idempotently ✓

**Client IP preservation through the chain:**
1. Entry Xray inbound has `xver: 1` → prepends PROXYv1 header with real client IP to data stream
2. Entry Xray VLESS outbound wraps `[PROXYv1 header + MTProto data]` in VLESS-Reality tunnel
3. Exit Xray VLESS inbound unwraps tunnel → raw data starts with PROXYv1 header
4. Exit Xray freedom outbound (proxyProtocol not set) forwards data as-is to telemt:8443
5. telemt (proxy_protocol=true) parses PROXYv1 header → extracts real client IP

This preserves per-IP quotas (`user_max_unique_ips`) and IP-based logging. ✓

### Artefacts

#### ADR-009: Encrypted Entry-to-Exit Segment via VLESS-Reality

```markdown
---
id: ADR-009
type: adr
status: proposed
created: 2026-07-03
---

# ADR-009: Encrypted Entry-to-Exit Segment via VLESS-Reality

## Context
ARCH-001@0.1.2 §3 C5 uses a `freedom` outbound on the entry server to redirect raw TCP to the exit server. This exposes MTProto byte patterns on the RU→EU international link (segment S2), where TSPU scrutiny is deepest. TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 and §6 document post-handshake payload analysis as an active TSPU capability since June 2026, and TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3 confirms production infrastructure "never sends raw proxy traffic on the RU→EU segment."

## Decision
We will replace the `freedom` outbound on the entry server with a VLESS-Reality outbound to the exit server, and add an Xray instance on the exit server (C7) to terminate this tunnel. The architecture becomes:

- **Entry:** Xray inbound (VLESS-Reality, :443, client-facing, `xver:1`) → Xray outbound (VLESS-Reality → exit:443)
- **Exit:** Xray inbound (VLESS-Reality, :443, from entry) → Xray outbound (freedom → telemt localhost:8443) + telemt on :8443 (internal) + Angie on :8080 (mask)

telemt moves from port 443 to 8443 (not externally exposed). Client IP is preserved via PROXYv1 (`xver:1` on entry inbound passes through the VLESS tunnel to telemt).

## Consequences
- **Positive:** MTProto patterns completely hidden from S2 DPI; international gateway sees only VLESS-Reality (standard HTTPS appearance).
- **Positive:** Post-handshake payload analysis — the strongest June 2026 detection vector — is fully mitigated.
- **Negative / cost:** Additional Xray process on exit server (minimal resource cost; Xray is lightweight). Exit deploy script becomes more complex (new prompts for exit Reality keys). 1–3 RTT connection setup overhead (one-time per persistent Telegram connection).
- **Follow-ups:** Exit server docker-compose switches to host network mode. Exit Xray needs its own X25519 keypair, VLESS UUID, and Reality SNI. Deploy-exit.sh must handle these new secrets. Entry Xray template changes from `freedom` to `vless` outbound.

## Alternatives considered
- **XHTTP-TLS transport** — viable alternative (wraps traffic in HTTP/2 over TLS). Deferred: VLESS-Reality is better documented, more widely deployed in production Russian proxy infrastructure, and the research §5 provides complete configs for it. XHTTP-TLS can be evaluated as a future transport option (research §10 "Explore Further" item 1).
- **Keep `freedom` (raw TCP)** — rejected: post-handshake payload analysis is active, federal operators at 0% success rate with unencrypted S2, production systems unanimously encrypt S2.
```

#### Full Xray config: Entry server (`infra/entry/xray-config.json.template` — encrypted S2 variant)

This is the complete replacement for the current entry template when encrypted S2 is enabled. It replaces the `freedom` outbound with a `vless` outbound and changes `xver` from 0 to 1 on the inbound.

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
      "tag": "vless-reality-in",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "__VLESS_UUID_ENTRY__",
            "level": 0,
            "email": "telemt-entry@default"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "__REALITY_SNI__:443",
          "xver": 1,
          "serverNames": [__REALITY_SERVER_NAMES__],
          "privateKey": "__REALITY_PRIVATE_KEY__",
          "minClientVer": "",
          "maxClientVer": "",
          "maxTimeDiff": 0,
          "shortIds": [__REALITY_SHORT_IDS__],
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
      "tag": "exit-relay",
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
        "outboundTag": "exit-relay",
        "network": "tcp,udp"
      }
    ]
  }
}
```

**Key differences from current template:**
- Inbound `xver` changed from `0` to `1` (prepends PROXYv1 with real client IP)
- Inbound uses `__VLESS_UUID_ENTRY__` (client-facing UUID) instead of `00000000-0000-0000-0000-000000000000`
- Outbound replaced: `freedom` with `proxyProtocol` → `vless` with Reality to exit server
- New placeholders: `__EXIT_VLESS_UUID__`, `__EXIT_REALITY_SNI__`, `__EXIT_SHORT_ID__`, `__EXIT_PUBLIC_KEY__`

#### Full Xray config: Exit server (`infra/exit/xray-config.json.template` — NEW file)

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
      "tag": "vless-reality-from-entry",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "__EXIT_VLESS_UUID__",
            "level": 0,
            "email": "entry-relay@default",
            "flow": "xtls-rprx-vision"
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
          "serverNames": [
            "__EXIT_REALITY_SNI__"
          ],
          "privateKey": "__EXIT_REALITY_PRIVATE_KEY__",
          "minClientVer": "",
          "maxClientVer": "",
          "maxTimeDiff": 0,
          "shortIds": [__EXIT_SHORT_IDS__],
          "fingerprint": "firefox"
        }
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
        "inboundTag": [
          "vless-reality-from-entry"
        ],
        "outboundTag": "to-telemt"
      }
    ]
  }
}
```

**Key design decisions:**
- `xver: 0` on exit inbound — does NOT add another PROXYv1 header. The PROXYv1 header from entry's `xver:1` passes through the VLESS tunnel as data and is forwarded as-is to telemt.
- No `proxyProtocol` on `to-telemt` freedom outbound — same reason: the PROXYv1 header is already in the data stream.
- `redirect: 127.0.0.1:8443` — telemt listens on localhost:8443 (host network mode).
- `flow: xtls-rprx-vision` on the client entry — matches the entry's outbound flow setting.
- `__EXIT_REALITY_SNI__` — should be a global CDN domain (e.g., `www.microsoft.com`) or self-steal domain; this is the SNI that TSPU sees on the RU→EU international link.

#### Updated exit docker-compose: `infra/exit/docker-compose.yml`

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# docker-compose.yml — Xray + telemt + Angie on the EU exit server.
#
# Encrypted S2 architecture (ADR-009):
#   Xray terminates VLESS-Reality from entry server on :443
#   Xray forwards decrypted traffic to telemt on localhost:8443
#   telemt handles MTProto/FakeTLS (internal, not externally exposed)
#   Angie serves mask host on :8080
#
# Host network mode: required so Xray can reach telemt on localhost:8443
# and UFW firewall rules apply directly.
#
# Per INV-DOCKER (project.jsonc invariants):
#   cap_drop: [ALL], read_only: true where possible,
#   security_opt: [no-new-privileges:true]
#   telemt/xray add cap_add: [NET_BIND_SERVICE]
# ─────────────────────────────────────────────────────────────────────────────

services:
  xray-exit:
    image: ghcr.io/xtls/xray-core:latest
    container_name: telemt-xray-exit
    network_mode: host
    restart: unless-stopped
    # ── Docker hardening (INV-DOCKER) ────────────────────────────────────
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:size=4M
    volumes:
      - ./xray-config.json:/etc/xray/config.json:ro
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  telemt:
    image: ghcr.io/telemt/telemt:latest
    container_name: telemt-exit
    network_mode: host
    restart: unless-stopped
    # ── Docker hardening (INV-DOCKER) ────────────────────────────────────
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp
    volumes:
      - ./config:/etc/telemt:rw
      - telemt-data:/var/lib/telemt:rw
    env_file:
      - .env
    ulimits:
      nofile:
        soft: 65536
        hard: 262144
    depends_on:
      - xray-exit
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  angie:
    image: angie/angie:latest
    container_name: telemt-mask
    network_mode: host
    restart: unless-stopped
    # ── Docker hardening (INV-DOCKER) ────────────────────────────────────
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp
      - /var/cache/angie
      - /var/run
    volumes:
      - ./mask:/var/www/mask:ro
      - ./angie.conf:/etc/angie/angie.conf:ro
    depends_on:
      - telemt
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  telemt-data:
```

**Key changes from current docker-compose:**
- Added `xray-exit` service (Xray VLESS-Reality termination)
- All services switched to `network_mode: host` (from bridge network with port mapping)
- Removed `ports:` sections (host network mode exposes directly)
- Removed `networks:` block (host network, no bridge)
- telemt `depends_on: xray-exit` (Xray must be running before telemt starts)

#### Config diff: `infra/exit/config.toml.template` (for encrypted S2)

**Old ([server] section — after TKT-015 changes):**
```toml
[server]
port = 443
```

**New:**
```toml
[server]
port = 8443
```

(All other config.toml changes from TKT-015 remain. Only the port changes for encrypted S2.)

#### Ticket: TKT-018

```markdown
---
id: TKT-018
type: ticket
status: draft
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-015]
estimate: L
created: 2026-07-03
---

# TKT-018: Encrypted Entry-to-Exit Segment via VLESS-Reality

## §1 Goal
Replace the `freedom` (raw TCP) outbound on the entry server with a VLESS-Reality encrypted tunnel to the exit server, and add an Xray instance on the exit server to terminate this tunnel and forward decrypted traffic to telemt on localhost:8443.

## §2 In Scope
- Replace entry `xray-config.json.template` with encrypted S2 variant:
  - Change inbound `xver` from `0` to `1` (PROXYv1 client IP preservation)
  - Replace `freedom` outbound with `vless` outbound (VLESS-Reality to exit)
  - Add new placeholders: `__VLESS_UUID_ENTRY__`, `__EXIT_VLESS_UUID__`, `__EXIT_REALITY_SNI__`, `__EXIT_SHORT_ID__`, `__EXIT_PUBLIC_KEY__`
- Create exit `xray-config.json.template` (new file):
  - VLESS-Reality inbound on :443 (from entry server)
  - Freedom outbound to `127.0.0.1:8443` (to telemt)
- Update exit `docker-compose.yml`:
  - Add `xray-exit` service container
  - Switch all services to host network mode
- Update exit `config.toml.template`: change port from 443 to 8443
- Update `deploy-entry.sh`: add prompts for exit VLESS UUID, exit Reality public key, exit Reality SNI, exit short ID
- Update `deploy-exit.sh`: add Xray keypair generation, VLESS UUID generation, xray-config.json generation from template, updated UFW rules

## §3 NOT In Scope
- XHTTP transport alternative (deferred per ADR-009)
- Angie SNI routing integration (handled by TKT-016)
- Self-steal domain for exit Reality SNI (handled by TKT-019; default: `www.microsoft.com`)
- Entry server docker-compose changes (Xray container unchanged)
- Monitoring stack changes (Prometheus scrapes same :9090)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5, C7
- ADR-009
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 (architecture, Xray configs, port conflict)
- TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3

## §5 Outputs
- `infra/entry/xray-config.json.template` (full replacement)
- `infra/entry/deploy-entry.sh` (exit server connectivity prompts)
- `infra/exit/xray-config.json.template` (new file)
- `infra/exit/docker-compose.yml` (updated: +xray-exit, host network)
- `infra/exit/config.toml.template` (port 443→8443)
- `infra/exit/deploy-exit.sh` (Xray setup, keypair generation, config generation)

## §6 Acceptance Criteria
- [ ] AC1 — Entry template inbound has `"xver": 1`
- [ ] AC2 — Entry template outbound protocol is `"vless"` (not `"freedom"`)
- [ ] AC3 — Entry template outbound has `"flow": "xtls-rprx-vision"` and `"security": "reality"`
- [ ] AC4 — Exit `xray-config.json.template` exists with VLESS-Reality inbound on :443
- [ ] AC5 — Exit Xray freedom outbound redirects to `127.0.0.1:8443` (no `proxyProtocol` field)
- [ ] AC6 — Exit `docker-compose.yml` includes `xray-exit` service with INV-DOCKER hardening
- [ ] AC7 — All services in exit `docker-compose.yml` use `network_mode: host`
- [ ] AC8 — Exit `config.toml.template` port is `8443`
- [ ] AC9 — `deploy-exit.sh` generates X25519 keypair for exit Xray (reusing the pattern from `deploy-entry.sh`)
- [ ] AC10 — `deploy-exit.sh` generates VLESS UUID for exit Xray (auto-generate with `uuidgen` or `xray uuid`)
- [ ] AC11 — `deploy-entry.sh` prompts for `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`
- [ ] AC12 — PROXYv1 client IP preservation verified: entry `xver:1` → VLESS tunnel → exit freedom → telemt `proxy_protocol=true` → real client IP in telemt logs
- [ ] AC13 — Both generated configs are valid JSON (`jq .` passes)
- [ ] AC14 — `deploy-exit.sh` is idempotent (INV-IDEMPOTENT)
- [ ] AC15 — All new secrets stored in `.env` (INV-SECRETS): `EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_SHORT_IDS`

## §7 Constraints
- telemt 3.4.22+ required
- Xray-core latest (ghcr.io/xtls/xray-core:latest)
- Host network mode required on exit server (for localhost:8443 communication between containers)
- No new pip/npm dependencies (deploy scripts only)

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
```

---

## Improvement 6: Self-Steal Domain Strategy for `tls_domain`

### Evaluation

**Research evidence — convincing.**
TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 provides a complete self-steal implementation guide including DNS setup, Let's Encrypt cert acquisition, Angie config sketch, and telemt config. The core argument: "TSPU's A-record cross-check passes by construction" — the A-record resolves to your own IP because you control the DNS. This eliminates the ASN mismatch vector that has already triggered MegaFon blocking for `github.com` (§2: "ASN mismatch confirmed to trigger MegaFon blocking [1]").

§2 ranks self-steal as the #1 FakeTLS domain candidate ("Eliminates ASN mismatch; requires domain + cert setup") above all third-party domains including `www.microsoft.com` (#2). The implementation guide provides concrete Angie config and telemt config blocks.

**Pros (from §2):** eliminates ASN mismatch entirely; operator controls rotation (update DNS TTL, swap A-record, restart telemt in ~30 seconds); no dependency on third-party TLS config changes breaking `tls_emulation`.

**Cons (from §2):** domain registration cost (low); domain may be blocked if associated with proxy activity (mitigate by using generic-looking domain name and rotating); requires DNS management overhead.

**Should this be the default or optional?**
Optional advanced config with `www.microsoft.com` as the new default. Rationale:
1. Self-steal requires domain registration, DNS management, and cert management — adding friction to the MVP deploy flow.
2. Not all operators have domain infrastructure ready.
3. `www.microsoft.com` (§2 #2 candidate) has "no Russian PoPs" for Azure CDN but stable TLS 1.3 and no known blocking reports — a safe default for operators who cannot set up self-steal.
4. The deploy script should offer self-steal as the recommended option with documentation, and fall back to `www.microsoft.com` if the operator skips domain setup.

**Architecture compatibility:** Changes deploy-exit.sh flow (new prompts for domain, cert setup). Adds optional Angie HTTPS config for serving the self-steal domain's TLS cert. Does not add a new component — it changes configuration within C5.

**PRD compliance:** R11 says `tls_domain` is "chosen by operator at deploy time (recommendations: github.com for EU exit, www.microsoft.com as backup)" — updating the recommendation from `github.com` to self-steal (with `www.microsoft.com` as default) is consistent with R11's approach. No Non-Goal violated.

**Interaction with Improvement 5 (encrypted S2):** §2 notes: "If the S2 segment is encrypted with VLESS-Reality (Section 5), TSPU sees only the outer VLESS-Reality handshake on S2, and `tls_domain` only matters for S3 — where there is no TSPU scrutiny at all." This means self-steal is *less critical* when encrypted S2 is adopted (since `tls_domain` only affects S3, which is outside Russia). However, self-steal still provides defense in depth: if the S2 encryption is ever compromised or bypassed, the `tls_domain` ASN match becomes the next line of defense. Implement as optional.

### Artefacts

#### ADR-010: Self-Steal Domain Strategy for `tls_domain`

```markdown
---
id: ADR-010
type: adr
status: proposed
created: 2026-07-03
---

# ADR-010: Self-Steal Domain Strategy for tls_domain

## Context
ARCH-001@0.1.2 §3 C5 uses `github.com` as the default `tls_domain` recommendation for the exit server. TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 documents that `github.com` (Azure CDN AS8075) creates an ASN mismatch against typical EU hosting (Hetzner AS24940), and MegaFon has already blocked connections based on this A-record cross-check [1]. The research proposes a "self-steal" strategy where the operator uses their own domain with DNS pointing to the exit server IP, eliminating ASN mismatch by construction.

## Decision
We will support an optional self-steal domain strategy in `deploy-exit.sh`:
1. Deploy script prompts the operator: "Do you have a domain for self-steal? (recommended for production)"
2. If yes: prompts for domain name, runs Let's Encrypt cert acquisition via Angie ACME, configures `tls_domain` to the operator's domain, sets up Angie to serve the TLS cert for `tls_emulation` fetching.
3. If no: defaults to `www.microsoft.com` (replacing `github.com` as the default recommendation).

Self-steal is documented as the recommended production approach; `www.microsoft.com` is the safe default for quick deployments.

## Consequences
- **Positive:** Eliminates ASN mismatch for operators who set up self-steal; TSPU A-record cross-check passes by construction.
- **Positive:** Operator controls domain rotation (DNS TTL update + telemt restart ≈ 30 seconds).
- **Negative / cost:** Requires domain registration and DNS management for self-steal. Adds Let's Encrypt cert management to exit server.
- **Follow-ups:** `deploy-exit.sh` must handle cert renewal (certbot/ACME cron or Angie's built-in ACME). If encrypted S2 (ADR-009) is also adopted, self-steal is less critical (tls_domain only matters for S3, outside Russia) but still recommended for defense in depth.

## Alternatives considered
- **Keep `github.com` as default** — rejected: ASN mismatch confirmed to trigger MegaFon blocking [1]; `www.microsoft.com` is strictly better as a third-party domain default.
- **Mandatory self-steal (no fallback)** — rejected: adds friction for operators without domain infrastructure; MVP should be deployable without domain registration.
```

#### Config diff: `infra/exit/deploy-exit.sh`

**Old (TLS_DOMAIN prompt):**
```bash
# TLS_DOMAIN — FakeTLS camouflage domain (with recommendations)
TLS_DOMAIN="$(prompt_for "TLS_DOMAIN" \
    "Enter FakeTLS domain (recommended: github.com primary, www.microsoft.com backup)" \
    "github.com")"
save_env_var "$ENV_FILE" "TLS_DOMAIN" "$TLS_DOMAIN"
```

**New:**
```bash
# TLS_DOMAIN — FakeTLS camouflage domain.
# Self-steal (operator-owned domain) is recommended for production.
# See docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2.
echo ""
echo "  FakeTLS domain (tls_domain) configuration:"
echo "    Option 1 (recommended): Self-steal domain — use your own domain"
echo "      (e.g. cdn.yourdomain.com) with DNS A-record → this server's IP."
echo "      Eliminates ASN mismatch; TSPU A-record check passes by construction."
echo "    Option 2 (default):     www.microsoft.com — safe third-party domain."
echo "      Works without domain setup but carries latent ASN mismatch risk."
echo ""
TLS_DOMAIN="$(prompt_for "TLS_DOMAIN" \
    "Enter FakeTLS domain (your domain for self-steal, or press Enter for default)" \
    "www.microsoft.com")"
save_env_var "$ENV_FILE" "TLS_DOMAIN" "$TLS_DOMAIN"

# Self-steal domain detection: if TLS_DOMAIN is not a known third-party domain,
# assume it's a self-steal domain and set up Let's Encrypt cert.
SELF_STEAL_DOMAIN=""
KNOWN_THIRD_PARTY="www.microsoft.com|github.com|www.apple.com|dl.google.com|www.twitch.tv"
if ! echo "$TLS_DOMAIN" | grep -qE "^($KNOWN_THIRD_PARTY)$"; then
    SELF_STEAL_DOMAIN="$TLS_DOMAIN"
    echo "✓ Self-steal domain detected: $SELF_STEAL_DOMAIN"
    echo "  Ensure DNS A-record for $SELF_STEAL_DOMAIN points to this server's IP."
    echo "  Let's Encrypt certificate will be obtained during deployment."
fi
save_env_var "$ENV_FILE" "SELF_STEAL_DOMAIN" "$SELF_STEAL_DOMAIN"
```

#### Ticket: TKT-019

```markdown
---
id: TKT-019
type: ticket
status: draft
arch_ref: ARCH-001@0.2.0
depends_on: [TKT-018]
estimate: M
created: 2026-07-03
---

# TKT-019: Self-Steal Domain Support for tls_domain

## §1 Goal
Add optional self-steal domain support to the exit server deploy script, enabling operators to use their own domain as `tls_domain` to eliminate ASN mismatch, and update the default third-party recommendation from `github.com` to `www.microsoft.com`.

## §2 In Scope
- Update `deploy-exit.sh` TLS_DOMAIN prompt with self-steal guidance and new default
- Add self-steal domain detection logic to `deploy-exit.sh`
- Add optional Let's Encrypt cert acquisition for self-steal domains (via certbot or Angie ACME)
- Add optional Angie HTTPS server block for serving TLS cert on self-steal domains
- Create `infra/exit/angie-selsteal.conf.template` (Angie config for self-steal HTTPS)
- Update `config.toml.template` `mask_host` and `mask_port` for self-steal mode
- Document self-steal setup in README.md

## §3 NOT In Scope
- Entry server self-steal domain (entry uses Reality SNI, not FakeTLS)
- Automated domain registration
- DNS provider integration (operator manages DNS manually or via existing Cloudflare scripts)
- Certbot renewal cron setup (document as manual step)

## §4 Inputs
- ARCH-001@0.2.0 §3 C5
- ADR-010
- TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 (self-steal implementation guide)

## §5 Outputs
- `infra/exit/deploy-exit.sh` (TLS_DOMAIN prompt, self-steal detection, cert setup)
- `infra/exit/angie-selsteal.conf.template` (new file: Angie HTTPS for self-steal)
- `infra/exit/config.toml.template` (mask_host, mask_port for self-steal mode)
- `README.md` (self-steal domain setup section)

## §6 Acceptance Criteria
- [ ] AC1 — Default TLS_DOMAIN is `www.microsoft.com` (not `github.com`)
- [ ] AC2 — Deploy script detects self-steal domain (not in known third-party list) and sets `SELF_STEAL_DOMAIN` env var
- [ ] AC3 — When SELF_STEAL_DOMAIN is set, deploy script prompts for DNS verification before proceeding
- [ ] AC4 — `angie-selsteal.conf.template` exists with TLS server block for the self-steal domain
- [ ] AC5 — Config template sets `mask_host = "$TLS_DOMAIN"` and `mask_port = 443` for self-steal mode
- [ ] AC6 — Config template sets `mask_host = "$TLS_DOMAIN"` and `mask_port = 8080` for third-party mode
- [ ] AC7 — README.md documents DNS A-record setup, Let's Encrypt cert acquisition, and self-steal advantages
- [ ] AC8 — `deploy-exit.sh` is idempotent (INV-IDEMPOTENT)

## §7 Constraints
- certbot or Angie ACME for Let's Encrypt
- DNS A-record must be configured by operator before cert acquisition (certbot HTTP-01 challenge)
- No new pip/npm dependencies

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green (typecheck/lint/test).
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-03 architect: ticket created from TSPU evasion evaluation session.
```

---

## ArchSpec Update: ARCH-001@0.1.2 → 0.2.0

### Frontmatter diff

**Old:**
```yaml
version: 0.1.2
adrs: [ADR-001@0.1.2, ADR-002@0.1.0, ADR-003@0.1.1, ADR-004@0.1.1, ADR-005@0.1.0, ADR-006@0.1.0, ADR-007@0.1.0]
tickets: [TKT-001@0.1.1, TKT-002@0.1.0, TKT-003@0.1.0, TKT-004@0.1.1, TKT-005@0.1.0, TKT-006@0.1.0, TKT-007@0.1.1, TKT-008@0.1.1, TKT-009@0.1.1, TKT-010@0.1.0, TKT-011@0.1.1, TKT-012@0.1.0, TKT-013@0.1.1]
```

**New:**
```yaml
version: 0.2.0
adrs: [ADR-001@0.1.2, ADR-002@0.1.0, ADR-003@0.1.1, ADR-004@0.1.1, ADR-005@0.1.0, ADR-006@0.1.0, ADR-007@0.1.0, ADR-008@0.2.0, ADR-009@0.2.0, ADR-010@0.2.0]
tickets: [TKT-001@0.1.1, TKT-002@0.1.0, TKT-003@0.1.0, TKT-004@0.1.1, TKT-005@0.1.0, TKT-006@0.1.0, TKT-007@0.1.1, TKT-008@0.1.1, TKT-009@0.1.1, TKT-010@0.1.0, TKT-011@0.1.1, TKT-012@0.1.0, TKT-013@0.1.1, TKT-014@0.2.0, TKT-015@0.2.0, TKT-016@0.2.0, TKT-017@0.2.0, TKT-018@0.2.0, TKT-019@0.2.0]
```

### §3 Component Addition

Add after C6:

```markdown
### C7 — Xray Exit Relay (encrypted S2 termination)

- **Responsibility:** Terminate the encrypted VLESS-Reality tunnel from the entry server on :443 and forward decrypted MTProto traffic to telemt on localhost:8443 via a `freedom` outbound. Presents a VLESS-Reality handshake with configurable SNI to TSPU on the RU→EU international link. Client IP is preserved: the entry server's `xver:1` prepends a PROXYv1 header to the data stream inside the VLESS tunnel; C7 forwards this header as-is to telemt.
- **Interface / contract:**
  - Listens on `0.0.0.0:443` (VLESS-Reality inbound, accepts connections from entry server only by UUID authentication)
  - Forwards decrypted traffic to `127.0.0.1:8443` (telemt, internal)
  - Requires: EXIT_VLESS_UUID (shared with entry server), EXIT_REALITY_PRIVATE_KEY, EXIT_REALITY_SNI, EXIT_SHORT_IDS
  - Error modes: connection refused if telemt is not listening on :8443; Reality handshake failure if UUID/keys mismatch
- **Depends on:** telemt (localhost:8443), Docker (Xray container)
- **Relevant ADRs:** ADR-009@0.2.0
```

### §3 C5 Update

Update C5 interface description:

**Add to `deploy-exit.sh` description:**
```
  - `infra/exit/deploy-exit.sh` — Telemt + Xray + Angie on EU exit server. Prompts for:
    domain, ad_tag, tls_domain (self-steal recommended; default: www.microsoft.com),
    telemt secret, exit Reality keys (auto-generates), exit VLESS UUID (auto-generates),
    exit Reality SNI, mask host config.
    Produces: Docker Compose + telemt config.toml + Xray config + Angie config.
```

**Add to `deploy-entry.sh` description:**
```
  - `infra/entry/deploy-entry.sh` — Xray VLESS-Reality on Russia entry server. Prompts for:
    exit server IP, Reality SNI (default: ads.x5.ru), Reality keys (auto-generates),
    exit VLESS UUID (from exit server deploy), exit Reality public key, exit Reality SNI,
    exit short ID. Produces: Docker Compose + Xray config.
```

### §9 Security — Threat Surfaces Update

Add row:

```markdown
| Xray exit (:443) | Entry server → exit server | VLESS UUID authentication (only entry server with correct UUID can connect). Reality key pair (X25519). UFW: allow 443/tcp from any (required for client connections that route through entry). |
```

Update telemt row port:
```markdown
| telemt (:8443) | Xray exit → localhost | Internal only, not exposed externally. localhost binding via Xray freedom redirect. proxy_protocol=true rejects connections without PROXY header. |
```

### §Revision Log Addition

```
- 2026-07-03 0.2.0 — TSPU evasion improvements: encrypted S2 via VLESS-Reality (ADR-009, C7), Russian Reality SNI (ads.x5.ru), PROXYv1, Angie SNI routing (ADR-008), RU datacenter guidance, self-steal domain strategy (ADR-010). 6 new tickets (TKT-014–TKT-019).
```

---

## Sequencing and Dependency Graph

```
Wave 6 (after existing Waves 1–5, all parallel-safe within wave):

  TKT-014 (S, I1: SNI)  ──┬──> TKT-015 (S, I2: PROXYv1) ──> TKT-018 (L, I5: Encrypted S2) ──> TKT-019 (M, I6: Self-steal)
                           │
                           └──> TKT-017 (S, I4: RU DC docs)

  TKT-016 (M, I3: SNI routing)  [independent, can run in parallel with all above]
```

**Parallel execution:** TKT-014 + TKT-016 can run in parallel (Wave 6a). TKT-015 + TKT-017 can run in parallel after TKT-014 completes (Wave 6b). TKT-018 after TKT-015 (Wave 6c). TKT-019 after TKT-018 (Wave 6d).

With concurrency_cap=3: TKT-014 + TKT-016 + TKT-017 could run in parallel if TKT-017's dependency on TKT-014 is relaxed (they touch different sections of deploy-entry.sh). However, to maintain disjoint outputs, TKT-017 waits for TKT-014.

---

## Verification Checklist

### 1. Every recommendation backed by a specific research section citation

| Improvement | Research citation |
|---|---|
| I1 (Russian SNI) | TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (top-10 candidates, `ads.x5.ru` validation, igareck whitelist 6 occurrences) |
| I2 (PROXYv1) | TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §4 (decision matrix, PROXYv2 5/10 vs PROXYv1 8/10, telemt §7 compat) |
| I3 (SNI routing) | TELEMT_TSPU_EVASION_PATTERNS.md Pattern 4 (production Angie stream routing) |
| I4 (RU datacenter) | TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (Selectel/Yandex.Cloud flag), §6 (Siberian module Signal 1) |
| I5 (Encrypted S2) | TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 (architecture, configs), §6 (post-handshake payload analysis); TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3 ("never sends raw proxy traffic on RU→EU") |
| I6 (Self-steal) | TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 (implementation guide, ASN mismatch evidence [1], MegaFon blocking) |

✅ All recommendations backed by specific sections.

### 2. No recommendation violates a PRD Non-Goal or project invariant

**PRD Non-Goals checked:**
- Paid access / billing — ✅ not affected
- User tiers — ✅ not affected
- User-facing stats — ✅ not affected
- Forking Bedolaga/Cabinet — ✅ not affected
- Integrating telemt into Remnawave — ✅ not affected
- tdlib-obf custom clients — ✅ not affected
- Web portal with registration — ✅ not affected
- Multi-server clustering — ✅ not affected (encrypted S2 is still single exit server)

**Invariants checked:**
- INV-AUTH — ✅ unchanged
- INV-SECRETS — ✅ new secrets (EXIT_VLESS_UUID, EXIT_REALITY_PRIVATE_KEY, SELF_STEAL_DOMAIN) via env vars
- INV-HASH — ✅ unchanged
- INV-DOMAIN — ✅ unchanged (proxy links still use domain names)
- INV-TIMEOUT — ✅ unchanged
- INV-ORM — ✅ unchanged
- INV-EMBED — ✅ unchanged
- INV-IDEMPOTENT — ✅ new prompts follow existing idempotent pattern
- INV-DOCKER — ✅ new Xray exit container follows hardening pattern
- INV-ASYNC — ✅ unchanged

✅ No violations.

### 3. New tickets have disjoint §5 Outputs and acyclic depends_on graph

| Ticket | §5 Outputs | Overlap resolution |
|---|---|---|
| TKT-014 | `xray-config.json.template` (inbound), `deploy-entry.sh` (SNI section) | — |
| TKT-015 | `xray-config.json.template` (outbound), `config.toml.template` (proxy settings) | Depends on TKT-014 (same file, different section) |
| TKT-016 | `angie-sni-router.conf.template` (new), `README.md` (SNI section) | Independent |
| TKT-017 | `deploy-entry.sh` (banner text), `README.md` (provider section) | Depends on TKT-014 (same file, different section) |
| TKT-018 | `xray-config.json.template` (full replace), `xray-config.json.template` (new exit), `docker-compose.yml` (exit), `config.toml.template` (port), `deploy-entry.sh` (exit prompts), `deploy-exit.sh` (Xray setup) | Depends on TKT-015 |
| TKT-019 | `deploy-exit.sh` (TLS_DOMAIN), `angie-selsteal.conf.template` (new), `config.toml.template` (mask settings), `README.md` (self-steal section) | Depends on TKT-018 |

**Dependency graph is acyclic:**
```
TKT-014 → TKT-015 → TKT-018 → TKT-019
TKT-014 → TKT-017
TKT-016 (independent)
```
No cycles. ✅

### 4. All version-pinned references use the correct version

- All new tickets: `arch_ref: ARCH-001@0.2.0` ✅
- New ADRs reference `ARCH-001@0.2.0` ✅
- ArchSpec frontmatter: `version: 0.2.0` ✅
- All existing ticket/ADR references in ArchSpec frontmatter retain their original versions ✅

### 5. Version bump: 0.1.2 → 0.2.0 (minor)

**Reason:** Improvement 5 (encrypted S2 via VLESS-Reality) adds a new component (C7: Xray Exit Relay) and changes the exit deploy topology (new container, port reassignment, network mode change). This is an architecture-level change warranting a minor version bump per the project's semver convention.

If Improvement 5 were not adopted, Improvements 1–4 and 6 are config/docs-level changes that would warrant a patch bump (0.1.2 → 0.1.3).

### 6. Improvement 5 configs provided

✅ Full Xray configs provided for:
- Entry server (encrypted S2 variant of `xray-config.json.template`)
- Exit server (new `xray-config.json.template`)
- Exit `docker-compose.yml` (updated with xray-exit service, host network mode)
- Exit `config.toml.template` port change (443 → 8443)

---

## Disagreements with Existing Knowledge Base

The original `TELEMT_FAKETLS_DOMAIN_SELECTION_REPORT.md` (skim) recommended `www.microsoft.com` (#1) and `github.com` (#2) as tls_domain candidates. The new research supersedes this on `github.com`: §2 of the new research documents ASN mismatch (Azure AS8075 vs Hetzner AS24940) as a confirmed MegaFon blocking trigger, downgrading `github.com` from a primary recommendation to a fallback. `www.microsoft.com` remains viable but carries the same latent ASN mismatch risk (Azure CDN).

The original report recommended `yahoo.com` as Reality SNI (#3). The new research strongly supersedes this: §1 documents `yahoo.com` as a geographic anomaly for RU-based entry servers and ranks it below Russian CDN domains (`ads.x5.ru` #1, `ya.ru` #2).

The original report's top-3 Reality SNI candidates (`www.microsoft.com` #1, `vkvideo.ru` #2, `yahoo.com` #3) are superseded by the new research's top-10 list which places Russian CDN domains first. `vkvideo.ru` remains viable (#10 in new list) but `ads.x5.ru` has stronger production validation (6 igareck occurrences vs 0 for vkvideo.ru).
