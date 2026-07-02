---
id: PRD-001
type: product_requirements
status: draft
version: 0.1.0
owner: PO
created: 2026-07-02
---

# PRD-001: Telemt MTProxy Management Layer

## §0 Decision Brief (30-second read for the PO)

- **What we're committing to:** A management layer for Telemt MTProxy — an embeddable Telegram bot package, an admin web panel, and infrastructure-as-code for deploying a free public Telegram proxy for Russian users. The proxy promotes the operator's Telegram channel via ad_tag.
- **Key tradeoffs:**
  1. Embeddable pip package vs separate bot only — we do both (package + standalone bot), enabling integration into any existing bot with 2 lines of code.
  2. Double-hop (Xray entry in RU → telemt exit in EU) vs single-hop — we commit to double-hop for DPI evasion, accepting the cost of an extra server.
  3. Admin web panel (React+TS) vs bot-only management — we build the panel because the operator needs labelled-link tracking, user management, and stats visualization that a bot cannot provide ergonomically.
- **Non-Goals (we are deliberately NOT doing):**
  - Paid access / billing (proxy is free for everyone)
  - User tiers / privileged vs free (all users equal in MVP; extension point in code)
  - User-facing stats (users receive only link + QR, nothing else)
  - Forking Bedolaga bot or Cabinet
  - Integrating telemt into Remnawave panel (technically impossible — Remnawave validates xray_version)
  - tdlib-obf custom client builds (deferred)
  - Web portal with registration for users (one-pager with "get proxy" button only)
- **Open business questions for the PO:** none at this stage.

## §1 Problem

Russian users of Telegram face ongoing DPI-based blocking (TSPU system, JA4/JA4+ fingerprinting since June 2026). The operator runs an existing VPN service (Remnawave + Bedolaga, 25 servers) and wants to offer a free Telegram-specific proxy as an additional channel — both as a public service and as a promotion vehicle for the operator's Telegram channel via the official MTProxy ad_tag mechanism.

There is no existing management layer that: (a) embeds into the operator's multiple Telegram bots, (b) provides an admin web panel for tracking labelled-link distribution, (c) deploys telemt with double-hop DPI evasion in one command, and (d) survives server migration without breaking user links.

## §2 Goals

- **G1** — Any Telegram user can obtain a personal MTProxy link via a bot button, without leaving the bot they're already in.
- **G2** — The operator can deploy a complete double-hop proxy (entry + exit + monitoring) on fresh servers via a single interactive script.
- **G3** — The operator can create labelled proxy links (e.g. "forum-4pda", "reddit-post") from the admin web panel and track per-label active users and traffic.
- **G4** — Proxy links never break when the exit server is migrated to a new IP (domain-based, DNS failover with TTL=60).
- **G5** — The operator can monitor proxy health, user count, traffic, and DPI-evasion effectiveness from a single Grafana dashboard.
- **G6** — The bot functionality can be added to any existing Telegram bot (operator's 5-6 stub bots, or Bedolaga bot) by installing a pip package and including an aiogram Router.
- **G7** — All users see the operator's promoted Telegram channel via ad_tag (official MTProxy proxy-promotion mechanism).

## §3 Non-Goals *(mandatory — at least one)*

- Paid access, billing, subscriptions, or payment integration for the proxy service.
- User tiers (privileged vs free) — deferred; code must have an extension point but no implementation in MVP.
- User-facing statistics, quota display, or usage dashboards.
- Forking or modifying the Bedolaga bot, Bedolaga Cabinet, or Remnawave panel.
- Registering telemt as a Remnawave node (not possible — Remnawave requires xray_version).
- Building or distributing custom Telegram clients (tdlib-obf).
- Full web portal with user registration/authentication — only a one-pager "get proxy" landing.
- Multi-server clustering or load balancing (single exit server in MVP; architecture must allow scaling but not implement it).

## §4 Users & Use Cases

**Primary users:**

1. **End user (Russian Telegram user)** — wants to connect to Telegram through a proxy that evades DPI blocking. Journey: encounters bot (or one-pager) → presses "Get Proxy" → receives `tg://proxy` link + QR code → taps link → Telegram connects. No account, no stats, no friction.

2. **Operator (admin)** — wants to deploy, monitor, and manage the proxy. Journeys:
   - Deploy: run `deploy.sh` on fresh server → answer prompts (domain, ad_tag, secrets) → proxy is live.
   - Create labelled link: open admin panel → "New Link" → enter label "forum-4pda" → get link + QR → post on forum → track usage from panel.
   - Monitor: open Grafana → see active users, traffic, bad connections, TLS fingerprints.
   - Migrate: run `migrate.sh` → proxy moves to new server → DNS updates → links still work.
   - Manage users: open admin panel → see all users, connections, traffic → disable abusers.

3. **Operator's existing bots** — the stub bots and (optionally) Bedolaga bot integrate the proxy package to offer "Get Proxy" alongside their existing functionality.

**Core journeys:**
- J1: End user obtains proxy link via bot button (most common).
- J2: End user obtains proxy link via one-pager web page.
- J3: Operator creates and tracks a labelled link for external distribution.
- J4: Operator deploys or migrates the proxy infrastructure.
- J5: Operator monitors proxy health and user activity.

## §5 Requirements

- **R1** — Embeddable Python package (`telemt_proxy`) exposing an aiogram Router with a "Get Proxy" button flow. (traces to G1, G6)
- **R2** — Standalone bot (`bot/`) using the package as a reference implementation. (traces to G1)
- **R3** — When a user requests a proxy link, the system creates a telemt user (POST /v1/users) with a pseudonymous SHA256-hashed identifier and returns a `tg://proxy` link + QR code. (traces to G1)
- **R4** — FastAPI backend (`api/`) providing admin endpoints: user list, create labelled link, disable user, aggregate stats, per-label stats. (traces to G3)
- **R5** — React + TypeScript admin web panel (`frontend/`) reusing Remnawave's design system, consuming the FastAPI backend. (traces to G3)
- **R6** — Labelled links are stored in PostgreSQL with: label name, telemt username, creation date, and are tracked via telemt per-user stats (connections, traffic, IPs). (traces to G3)
- **R7** — Interactive deploy script (`scripts/deploy.sh`) that prompts for domain, ad_tag, telemt secret, Cloudflare API token, and generates config from templates. (traces to G2)
- **R8** — Docker Compose for exit server (telemt + Angie mask host + Prometheus + Grafana) and entry server (Xray VLESS-Reality, fingerprint=firefox). (traces to G2)
- **R9** — Migration script (`scripts/migrate.sh`) that: stops containers, tars config/state, transfers to new server, deploys, updates Cloudflare DNS A-record via API. Total downtime < 2 minutes. (traces to G4)
- **R10** — Proxy links use a domain name (e.g. `tg-proxy.example.com`) with Cloudflare DNS-only (grey cloud), TTL=60s. Links contain domain, not IP. (traces to G4)
- **R11** — Telemt config with FakeTLS enabled, mask_host pointing to local Angie, ad_tag set to operator's channel tag from @MTProxybot. (traces to G7)
- **R12** — Xray entry server in Russia with VLESS-Reality inbound, PROXYv2 forwarding to exit server, fingerprint=firefox. (traces to G2)
- **R13** — Grafana dashboard (importing #25119 or repo's grafana-dashboard-by-user.json) showing: active users, connections, traffic, bad connection ratio, per-user stats. (traces to G5)
- **R14** — Admin panel embeds or links to Grafana dashboard for unified monitoring view. (traces to G5)
- **R15** — One-pager web page (served by Angie) with a single "Get Proxy" button that redirects to the standalone bot. (traces to G1)
- **R16** — All user identifiers in telemt are `sha256(telegram_id + salt)[:16]` — never raw Telegram IDs. (security invariant)
- **R17** — Telemt API (:9091) accessible only from management server IP (firewall + whitelist + auth_header). (security invariant)
- **R18** — Code architecture includes a documented extension point for user tiers (Tier 1: VPN subscribers, Tier 2: public free) without implementing it in MVP. (future-proofing)

## §6 Success Metrics

- **M1** — Deploy script produces a working proxy on a fresh Ubuntu/Debian server in < 10 minutes (measured: time from script start to first successful Telegram connection through proxy).
- **M2** — Migration script completes with < 2 minutes of user-facing downtime (measured: time from old server stop to new server accepting connections + DNS propagation).
- **M3** — Bot package integrates into an existing aiogram bot with ≤ 3 lines of code (measured: lines added to existing bot's main.py).
- **M4** — Admin panel loads user list with 1000+ users in < 2 seconds (measured: API response time).
- **M5** — Proxy links work after migration without any user action (measured: user reconnects after DNS TTL expiry without receiving a new link).
- **M6** — Channel subscriber growth attributable to ad_tag (measured: @MTProxybot stats vs. total proxy user count).

## §7 Constraints & Assumptions

- **Hosting:** Hetzner CX22 (2vCPU/4GB, ~€4.5/mo) for exit server; cheap RU VPS (1vCPU/1GB) for entry server. Operator has existing servers available.
- **DNS:** Cloudflare DNS-only (grey cloud, no proxy). Operator has domains on Cloudflare.
- **Telegram channel:** Must be public for @MTProxybot registration.
- **JA4 blocking:** Standard Telegram clients may still be blocked; the proxy + double-hop addresses server-side evasion, but client-side JA4 is out of scope (deferred to tdlib-obf or local DPI tools).
- **Telemt version:** 3.4.22 (latest as of July 2026). License: TELEMT LICENSE 3.3 (not MIT — trademark protected, patent grant with defensive termination).
- **Bedolaga:** 184 releases, active development. We do NOT fork it. We use its Web API (X-API-Key) only if tier functionality is implemented later.
- **Remnawave:** Cannot register telemt as a node (xray_version validation). Telemt monitoring is separate from Remnawave monitoring.
- **Capacity:** ~160-200 concurrent users on 2vCPU/4GB with default ulimit. Requires `ulimit -n 65536` for ~6400-8000 users.
- **Angie:** Used for mask_host (HTTP stub on :8080) and admin panel reverse proxy (auto-cert on :8443 → FastAPI :8000).

## §8 Risks

- **R-1 JA4 client blocking persists** → proxy works but users with standard clients can't connect. Mitigation: document GoodbyeDPI/zapret/ByeDPI as client-side workarounds; plan tdlib-obf for phase 2.
- **R-2 Entry server IP blocked by RKN** → users can't reach the tunnel. Mitigation: deploy backup entry server; migrate.sh can repoint DNS to new entry.
- **R-3 tls_domain detected by TSPU** → FakeTLS fingerprint blocked. Mitigation: rotate tls_domain (one-line config change + restart); research ongoing for optimal domain selection.
- **R-4 ad_tag revoked by @MTProxybot** → channel promotion stops. Mitigation: maintain backup channel; re-register with @MTProxybot.
- **R-5 Bedolaga API breaking change** → if tier functionality is added later, the Bedolaga Web API endpoint may change. Mitigation: pin API version; add integration test.
- **R-6 Telegram DNS caching on Desktop** → after migration, Desktop users may need to restart Telegram (Issue #30494). Mitigation: document in FAQ; links still "work" after restart.
- **R-7 Telemt license change** → TELEMT LICENSE 3.3 may change terms. Mitigation: pin telemt version; monitor releases.

## §9 Revision Log

- 2026-07-02 0.1.0 — initial draft.
