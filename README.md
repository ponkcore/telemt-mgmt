# telemt-mgmt

Management layer for **Telemt MTProxy** — embeddable Telegram bot package, admin web
panel, and infrastructure-as-code for deploying a free public Telegram proxy targeting
Russian users behind DPI censorship (TSPU).

The proxy promotes the operator's Telegram channel via the official MTProxy `ad_tag`
mechanism. Built on [telemt](https://github.com/telemt/telemt) 3.4.22 with double-hop
Xray VLESS-Reality for DPI evasion.

## What's in the box

| Component | Path | What it does |
|---|---|---|
| `telemt_proxy` package | `telemt_proxy/` | Embeddable Python package: aiogram Router with "Get Proxy" flow, TelemtClient (httpx wrapper), QR generation, user-ID hashing, SQLAlchemy models. `pip install` + 3 lines to embed in any aiogram bot. |
| Standalone bot | `bot/` | Reference bot implementation using the package. Long-polling, env-var config. |
| Admin API | `api/` | FastAPI backend: JWT auth, user management, labelled-link CRUD, aggregate/per-label stats. |
| Admin panel | `frontend/` | React + TypeScript SPA: dashboard, users, links, Grafana embed. Dark theme. |
| Deploy scripts | `infra/` | 5 independent interactive scripts (exit, entry, mgmt, monitoring, landing) + Docker Compose for each. |
| Migration | `scripts/` | `migrate.sh` + `cloudflare-dns.sh` — move proxy to new server, update DNS, <2 min downtime. |

## Architecture (double-hop)

```
Telegram client
    │
    ▼
[Entry server — Russia]          Xray VLESS-Reality (port 443)
    │                             Reality SNI: vkvideo.ru / yahoo.com
    │                             fingerprint: firefox
    ▼ (VLESS-Reality tunnel)
[Exit server — EU]               telemt 3.4.22 (port 8443, PROXYv2)
    │                             FakeTLS: tls_domain=github.com
    │                             ad_tag from @MTProxybot
    │                             Angie mask_host on :8080
    ▼
Telegram DCs

[Mgmt server]                     Bot + FastAPI + PostgreSQL + admin panel
[Monitoring server]              Prometheus + Grafana (scrapes exit :9090)
```

TSPU sees only the encrypted VLESS-Reality tunnel to the Russian entry server. The EU
exit server and Telegram DC connections are invisible to Russian DPI.

## Quick start (development)

### Prerequisites

- NixOS (or Linux/macOS with `uv` + Node 22 + Python 3.12)
- On NixOS: just run `nix-shell` — it sets up everything including `LD_LIBRARY_PATH`
  for C-extension wheels

### Setup

```bash
# On NixOS — enters dev shell with uv, node, python, libstdc++
nix-shell

# Install dependencies
uv sync && cd frontend && npm ci

# Run checks
uv run mypy --strict telemt_proxy api bot
uv run ruff check telemt_proxy api bot tests
uv run pytest -q
```

### Project commands (all run inside `nix-shell` on NixOS)

| Command | What |
|---|---|
| `nix-shell --run 'uv sync && cd frontend && npm ci'` | Install all deps |
| `nix-shell --run 'uv run pytest -q'` | Run tests (198 passing) |
| `nix-shell --run 'uv run mypy --strict telemt_proxy api bot'` | Type-check |
| `nix-shell --run 'uv run ruff check telemt_proxy api bot tests'` | Lint |
| `nix-shell --run 'cd frontend && npm run build'` | Build frontend |

## Deploy (production)

Five independent scripts, each runs on a fresh Ubuntu/Debian server. Interactive —
prompts for domain, ad_tag, secrets on first run, reads `.env` on re-runs.

```bash
# 1. Exit server (EU) — telemt + Angie mask host
bash infra/exit/deploy-exit.sh

# 2. Entry server (Russia) — Xray VLESS-Reality
bash infra/entry/deploy-entry.sh

# 3. Management server — bot + API + panel + PostgreSQL
bash infra/mgmt/deploy-mgmt.sh

# 4. Monitoring server — Prometheus + Grafana
bash infra/monitoring/deploy-monitoring.sh

# 5. Landing page (any server) — static one-pager
bash infra/landing/deploy-landing.sh
```

### Prerequisites for deploy

- Hetzner CX22 (2vCPU/4GB) for exit server
- Cheap RU VPS (1vCPU/1GB) for entry server
- Domain on Cloudflare (DNS-only, grey cloud, TTL=60)
- Telegram bot token from @BotFather
- ad_tag from @MTProxybot (requires public channel)
- Cloudflare API token (for migration script)

### Landing page deployment

The landing page is a static one-pager served by Angie via Docker Compose. It
links to your Telegram bot so users can get a proxy via a "Получить прокси"
button. Deploy on any server (can share with the management server):

```bash
bash infra/landing/deploy-landing.sh
```

The script prompts for:
- **BOT_URL** — Telegram bot URL (e.g. `https://t.me/myproxybot`)
- **DOMAIN** — domain for HTTPS (optional; leave empty for HTTP-only)

If a domain is provided, the script obtains a Let's Encrypt certificate via
certbot and configures Angie for HTTPS. Idempotent — re-run to update the
bot URL or domain.

### Russian Entry Server Provider Selection

The entry server must be hosted in Russia (Russian ASN, Russian A-record for the
Reality SNI). However, not all Russian datacenter providers are equal: the June 2026
TSPU "Siberian" behavioral module flags certain hosting provider subnets as
**Signal 1** (suspicious server subnet). When Signal 1 is active, the operator must
keep Signals 2 (TLS fingerprint) and 3 (connection burst) clean to avoid a
120-second connection freeze — and the freeze doubles to 600 seconds if the client
rotates its TLS fingerprint during the event.

#### Provider comparison

| Provider | Signal 1 Status | Notes |
|---|---|---|
| **Beget** | Not flagged | Recommended. Russian hosting, not on the TSPU flagged subnet list. |
| **TimeWeb** | Not flagged | Recommended. Russian hosting, not on the TSPU flagged subnet list. |
| **reg.ru** | Not flagged | Recommended. Russian hosting, not on the TSPU flagged subnet list. |
| **Selectel** | **Flagged (Signal 1)** | Avoid for entry servers. Subnet explicitly flagged by the June 2026 Siberian module. Signal 1 is always active regardless of SNI choice. |
| **Yandex.Cloud** | **Flagged (Signal 1)** | Avoid for entry servers. Subnet explicitly flagged by the June 2026 Siberian module. Signal 1 is always active regardless of SNI choice. |

> **What is Signal 1?** The June 2026 TSPU behavioral module triggers a
> 120-second connection freeze when three signals coincide (logical AND):
> Signal 1 (suspicious server subnet), Signal 2 (suspicious TLS fingerprint —
> Chrome is highly suspicious post-June 2026), and Signal 3 (more than 3 parallel
> TLS handshakes to the same SNI within 60 seconds with inter-connection delays
> under 350–400 ms). On a flagged subnet (Signal 1 active), the operator must keep
> Signals 2 and 3 clean — use the `firefox` fingerprint and keep connection
> parallelism under 3.
>
> **Reference:** [TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md](docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md)
> §1 (Selectel/Yandex.Cloud flag note) and §6 (Siberian behavioral module).

## Shared-server deployment (optional)

By default, telemt owns port 443 exclusively on the exit server (**standalone
mode**). For operators who need to co-locate telemt with other TLS-based services
on a single server, an optional **shared mode** uses Angie SNI stream routing to
multiplex port 443 across multiple services by their TLS SNI domain.

### Standalone vs. shared mode

| Aspect | Standalone (default) | Shared (optional) |
|---|---|---|
| Who owns :443 | telemt directly | Angie (SNI routing) |
| telemt listen port | 443 | 8443 (internal, not exposed) |
| Angie role | Mask host on :8080 only | SNI routing on :443 + mask host on :8080 |
| Config template | `angie.conf.template` | `angie-sni-router.conf.template` |
| config.toml port | 443 | 8443 |
| docker-compose ports | telemt: `"443:443"` | angie: `"443:443"`, telemt: `"8443:8443"` |
| Other TLS services on :443 | Not possible | Yes — one SNI per service |
| Complexity | Simple | Moderate (SNI map management) |
| When to use | Dedicated exit server | Shared server / cost optimization |

### How SNI routing works

Angie reads the SNI (Server Name Indication) field from the TLS ClientHello
**without decrypting** the traffic — no certificates, no keys, no plaintext.
It routes the raw TCP stream to the matching backend, which terminates its own
TLS:

```
Client → :443 → Angie stream (ssl_preread on)
                 ├─ SNI=proxy.example.com    → 127.0.0.1:8443 (telemt)
                 ├─ SNI=other.example.com    → 127.0.0.1:8445 (other service)
                 └─ default (unknown SNI)    → 127.0.0.1:8443 (telemt)
```

### Deploying in shared mode

The shared-mode template is **not wired into `deploy-exit.sh`** — the operator
manually selects and configures it. Steps:

1. Copy the template: `cp infra/exit/angie-sni-router.conf.template infra/exit/angie.conf`
2. Replace `__TELEMT_SNI__` with your telemt service domain
3. Add additional SNI entries for co-located services
4. Edit `config.toml`: change `port = 443` to `port = 8443`
5. Edit `docker-compose.yml`: move `"443:443"` from the telemt service to the
   angie service, add `"8443:8443"` to telemt
6. Run `docker compose up -d`

See `infra/exit/angie-sni-router.conf.template` for full inline documentation.

> **Reference:** [ADR-008](docs/architecture/adr/ADR-008-angie-sni-routing-shared-exit.md)
> documents the architectural decision. Production validation is in
> [TELEMT_TSPU_EVASION_PATTERNS.md](docs/knowledge/TELEMT_TSPU_EVASION_PATTERNS.md) Pattern 4.


## Self-steal domain (recommended for production)

By default, `deploy-exit.sh` uses a third-party domain (`www.microsoft.com`) as
the `tls_domain` for FakeTLS camouflage. This works, but creates an **ASN
mismatch**: the domain's A-record resolves to a third-party CDN (e.g.
Microsoft Azure AS8075) while the actual TCP connection originates from your
exit server (e.g. Hetzner AS24940). MegaFon has blocked connections based on
this A-record cross-check.

**Self-steal** eliminates this mismatch entirely: you register a domain, point
its A-record to your exit server's IP, obtain a TLS certificate, and set
`tls_domain` to your own domain. telemt's `tls_emulation` then fetches the
ServerHello from your own server — the A-record resolves to your server's IP,
so the ASN is identical to the actual connection's ASN. TSPU's A-record
cross-check passes by construction.

### When to use self-steal

| Scenario | Use self-steal? | Why |
|---|---|---|
| Production deployment | **Yes** (recommended) | Eliminates ASN mismatch — the strongest TSPU evasion |
| Quick test / development | No | Third-party default (`www.microsoft.com`) is faster to set up |
| No domain available | No | Use `www.microsoft.com` (safe default, no ASN mismatch on most ISPs) |

### Setup steps

1. **Register a domain** (e.g. `cdn.example.com`). Use a generic-looking name
   that doesn't attract attention. Any registrar works — the domain only needs
   DNS management.

2. **Configure DNS A-record** pointing to your exit server's IP:
   ```
   cdn.example.com  A  <exit-server-IP>  TTL=300
   ```
   Set TTL to 300 seconds (5 minutes) for fast rotation. If using Cloudflare,
   set the DNS record to **DNS-only (grey cloud)** — the A-record must resolve
   directly to your server IP, not Cloudflare's proxy IPs.

3. **Run `deploy-exit.sh`** and enter your domain when prompted for
   `TLS_DOMAIN`:
   ```
   Enter FakeTLS domain (default: www.microsoft.com, or your own domain for self-steal): cdn.example.com
   ```
   The script automatically:
   - Detects that `cdn.example.com` is not in the known third-party list
   - Prompts you to confirm the DNS A-record is configured
   - Obtains a Let's Encrypt certificate via `certbot` (HTTP-01 challenge)
   - Generates `angie-selsteal.conf` with a TLS server block on :443
   - Sets `mask_host = "cdn.example.com"` and `mask_port = 443` in `config.toml`

4. **Set up cert renewal** (manual — NOT automated by the deploy script):
   ```bash
   # Add to crontab on the exit server:
   0 3 * * * certbot renew && docker restart telemt-mask
   ```
   Certbot renew checks daily; certificates renew at 30 days before expiry.

### How it works

```
Telegram client → entry server (VLESS-Reality) → exit server
                                                    │
                                                    ├─ Xray-exit :443 (VLESS-Reality inbound)
                                                    ├─ telemt :8443 (FakeTLS/MTProto)
                                                    │   tls_domain = "cdn.example.com"
                                                    │   mask_host = "cdn.example.com"
                                                    │   mask_port = 443
                                                    │   tls_emulation fetches ServerHello
                                                    │   from cdn.example.com:443 ↓
                                                    └─ Angie :443 (TLS cert for cdn.example.com)
                                                        ssl_certificate = /etc/letsencrypt/live/cdn.example.com/fullchain.pem
                                                        → returns real ServerHello to telemt

TSPU sees: SNI=cdn.example.com, A-record → exit server IP, ASN = exit server's ASN ✓
```

### Advantages

- **Eliminates ASN mismatch** — the strongest TSPU A-record cross-check evasion
- **Operator controls rotation** — update DNS A-record (TTL=300s), restart
  telemt (~30 seconds), propagation in ~5 minutes. Total downtime: under 6
  minutes.
- **No dependency on third-party TLS config** — `tls_emulation` always succeeds
  because you control the TLS server
- **Defense in depth** — even with encrypted S2 (VLESS-Reality), self-steal
  adds an additional layer of ASN consistency on the S3 segment

### Third-party domain default

If you don't use self-steal, `deploy-exit.sh` defaults to `www.microsoft.com`
(previously `github.com`). The change was made because `github.com` (Azure
AS8075) creates an ASN mismatch on Hetzner exit servers that MegaFon has
already acted on. `www.microsoft.com` is on the same Azure CDN but has not
been specifically targeted, and is a higher-traffic domain with more stable
TLS 1.3 characteristics.

> **Reference:** [ADR-010](docs/architecture/adr/ADR-010-self-steal-domain-strategy.md)
> documents the architectural decision.
> [TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md](docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md)
> §2 contains the full self-steal implementation guide and domain selection
> rationale.


## Embed in an existing bot

```python
from telemt_proxy.router import create_router
from telemt_proxy.config import ProxyConfig

config = ProxyConfig(server="proxy.example.com", port=443, salt=os.environ["HASHING_SALT"])
router = create_router(telemt_client, db_session_factory, config)
dp.include_router(router)
```

The package is also installable as a pip package (`telemt_proxy`).

## Tech stack

| Layer | Tech |
|---|---|
| Bot | Python 3.12, aiogram 3.x |
| API | Python 3.12, FastAPI, uvicorn |
| Database | PostgreSQL 16, SQLAlchemy 2.x async, asyncpg, Alembic |
| Frontend | TypeScript, React, Vite |
| Proxy engine | telemt 3.4.22 (Rust, Docker) |
| DPI evasion | Xray VLESS-Reality (entry) + FakeTLS (exit) |
| Monitoring | Prometheus + Grafana 12.4.2 |
| Reverse proxy | Angie (mask host, panel TLS, landing) |
| DNS | Cloudflare DNS-only (TTL=60) |
| Package manager | uv (Python), npm (frontend) |
| Containers | Docker Compose (per deploy target) |

## Project structure

```
telemt-mgmt/
├── telemt_proxy/          # embeddable package (router, client, models, qr, hashing, link)
├── bot/                   # standalone bot reference implementation
├── api/                   # FastAPI admin backend
├── frontend/              # React + TS admin panel
├── infra/
│   ├── exit/              # telemt + Angie deploy
│   ├── entry/             # Xray VLESS-Reality deploy
│   ├── mgmt/              # bot + API + panel + PostgreSQL deploy
│   ├── monitoring/        # Prometheus + Grafana deploy
│   ├── landing/           # static one-pager deploy
│   └── lib/common.sh      # shared deploy helpers
├── scripts/
│   ├── migrate.sh         # server migration + DNS update
│   └── cloudflare-dns.sh  # Cloudflare API helper
├── tests/                 # 13 test files, 198 tests
├── alembic/               # DB migrations
├── docs/                  # PRD, ArchSpec, ADRs, tickets, knowledge base
├── shell.nix              # NixOS dev shell
└── pyproject.toml         # Python project config
```

## Development pipeline

This project uses a four-role SDLC pipeline (Business Planner → Technical Architect →
Sisyphus orchestrator → reviewer). All design artefacts are version-controlled markdown.

- PRD-001@0.3.0 (approved) — product requirements
- ARCH-001@0.1.2 (approved) — architecture spec + 7 ADRs
- 13 tickets, all `done` — 13 PRs merged

See `AGENTS.md` and `CONTRIBUTING.md` for the full process.

## License

MIT (project code). Telemt itself uses TELEMT LICENSE 3.3 (not MIT — trademark
protected, patent grant with defensive termination).
