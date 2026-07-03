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
