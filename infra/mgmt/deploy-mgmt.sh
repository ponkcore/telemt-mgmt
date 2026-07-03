#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy-mgmt.sh — deploy the management server stack.
#
# Deploys bot + admin API + admin panel + PostgreSQL via Docker Compose,
# fronted by Angie reverse proxy with Let's Encrypt TLS.
#
# Prompts for (AC2):
#   TELEMT_API_URL      — URL of the telemt REST API on the exit server
#   TELEMT_AUTH_HEADER  — Authorization header value for the telemt API
#   BOT_TOKEN           — Telegram bot token from @BotFather
#   DATABASE_URL        — SQLAlchemy async URL (auto-creates PG if empty, AC3)
#   PANEL_DOMAIN        — domain for the admin panel (AC5: HTTPS via Let's Encrypt)
#   ADMIN_USERNAME      — initial admin username for JWT auth (ADR-002@0.1.0)
#   ADMIN_PASSWORD      — initial admin password (bcrypt-hashed on startup)
#   TELEMT_PROXY_SERVER — entry server FQDN for proxy links (INV-DOMAIN)
#   TELEMT_PROXY_PORT   — entry server port for proxy links
#
# Idempotent (AC1): reads .env on re-run, skips prompts for already-set vars.
# Alembic migrations run on container startup (AC4).
# Bot starts via long polling (AC6).
# Panel accessible via HTTPS (AC5).
#
# Per INV-DOCKER: all containers use cap_drop: ALL, read_only: true where
# possible, security_opt: no-new-privileges:true.
# Per §7 Constraints: PostgreSQL image postgres:16-alpine, Python python:3.12-slim.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Resolve script directory (handles symlinks) ──────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$INFRA_DIR/.." && pwd)"

# Source shared helpers (infra/lib/common.sh).
# shellcheck disable=SC1091
source "$INFRA_DIR/lib/common.sh"

# ── Paths ───────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
ANGIE_TEMPLATE="$SCRIPT_DIR/angie.conf.template"
ANGIE_CONF="$SCRIPT_DIR/angie.conf"
FRONTEND_DIST="$REPO_DIR/frontend/dist"

# ── Helper: generate self-signed certificate (fallback if certbot unavailable) ─
_generate_self_signed() {
    local domain="$1"
    local cert_dir="$2"
    mkdir -p "$cert_dir"
    if command -v openssl &>/dev/null; then
        openssl req -x509 -nodes -days 365 \
            -newkey rsa:2048 \
            -keyout "$cert_dir/privkey.pem" \
            -out "$cert_dir/fullchain.pem" \
            -subj "/CN=${domain}" 2>/dev/null
        echo "  ✓ Self-signed certificate generated for ${domain}."
    else
        echo "ERROR: openssl not found. Cannot generate certificate." >&2
        exit 1
    fi
}

# ── Pre-flight ──────────────────────────────────────────────────────────────
check_docker

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  telemt-mgmt — Management Server Deploy                       ║"
echo "║  (Bot + API + Panel + PostgreSQL + Angie)                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Load existing config (AC1: idempotent re-run detection) ─────────────────
# INV-IDEMPOTENT: load_env sources .env if it exists; prompt_for skips prompts
# when the variable is already set.
load_env "$ENV_FILE"

# ── Prompt for configuration (AC2) ──────────────────────────────────────────

# TELEMT_API_URL — telemt REST API URL on the exit server.
TELEMT_API_URL="$(prompt_for "TELEMT_API_URL" \
    "Enter telemt API URL (e.g. http://exit.example.com:9091)")"
save_env_var "$ENV_FILE" "TELEMT_API_URL" "$TELEMT_API_URL"

# TELEMT_AUTH_HEADER — shared secret for the telemt API (INV-AUTH).
TELEMT_AUTH_HEADER="$(prompt_for "TELEMT_AUTH_HEADER" \
    "Enter telemt auth_header (shared secret for API)")"
save_env_var "$ENV_FILE" "TELEMT_AUTH_HEADER" "$TELEMT_AUTH_HEADER"

# BOT_TOKEN — Telegram bot token from @BotFather.
BOT_TOKEN="$(prompt_for "BOT_TOKEN" \
    "Enter Telegram bot token from @BotFather")"
save_env_var "$ENV_FILE" "BOT_TOKEN" "$BOT_TOKEN"

# PANEL_DOMAIN — domain for the admin panel (AC5: HTTPS via Let's Encrypt).
PANEL_DOMAIN="$(prompt_for "PANEL_DOMAIN" \
    "Enter panel domain (e.g. panel.example.com)")"
save_env_var "$ENV_FILE" "PANEL_DOMAIN" "$PANEL_DOMAIN"

# ADMIN_USERNAME — initial admin username for JWT auth (ADR-002@0.1.0).
ADMIN_USERNAME="$(prompt_for "ADMIN_USERNAME" \
    "Enter initial admin username")"
save_env_var "$ENV_FILE" "ADMIN_USERNAME" "$ADMIN_USERNAME"

# ADMIN_PASSWORD — initial admin password (bcrypt-hashed on startup).
ADMIN_PASSWORD="$(prompt_for "ADMIN_PASSWORD" \
    "Enter initial admin password")"
save_env_var "$ENV_FILE" "ADMIN_PASSWORD" "$ADMIN_PASSWORD"

# TELEMT_PROXY_SERVER — entry server FQDN for proxy links (INV-DOMAIN).
TELEMT_PROXY_SERVER="$(prompt_for "TELEMT_PROXY_SERVER" \
    "Enter entry server FQDN for proxy links (e.g. entry.example.com)")"
save_env_var "$ENV_FILE" "TELEMT_PROXY_SERVER" "$TELEMT_PROXY_SERVER"

# TELEMT_PROXY_PORT — entry server port for proxy links.
TELEMT_PROXY_PORT="$(prompt_for "TELEMT_PROXY_PORT" \
    "Enter entry server port for proxy links" \
    "443")"
save_env_var "$ENV_FILE" "TELEMT_PROXY_PORT" "$TELEMT_PROXY_PORT"

# ── DATABASE_URL: auto-create PostgreSQL if not provided (AC3) ──────────────
if [[ -n "${DATABASE_URL:-}" ]]; then
    echo "✓ DATABASE_URL already set (from .env). Using external database."
else
    echo "→ DATABASE_URL not provided. Auto-creating PostgreSQL container (AC3)."
    # Generate a random password for the auto-created PostgreSQL.
    POSTGRES_PASSWORD="$(generate_secret 16)"
    save_env_var "$ENV_FILE" "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"
    # Set DATABASE_URL to point at the Docker Compose 'db' service.
    DATABASE_URL="postgresql+asyncpg://telemt:${POSTGRES_PASSWORD}@db:5432/telemt"
    save_env_var "$ENV_FILE" "DATABASE_URL" "$DATABASE_URL"
    echo "✓ Auto-created DATABASE_URL pointing to Docker PostgreSQL container."
fi
export DATABASE_URL

# ── Generate HASHING_SALT if not set (INV-HASH) ─────────────────────────────
if [[ -n "${HASHING_SALT:-}" ]]; then
    echo "✓ HASHING_SALT already set (from .env)."
else
    HASHING_SALT="$(generate_secret 32)"
    save_env_var "$ENV_FILE" "HASHING_SALT" "$HASHING_SALT"
    echo "✓ Generated HASHING_SALT (64 hex chars)"
fi
export HASHING_SALT

# ── Generate JWT_SECRET_KEY if not set (ADR-002@0.1.0) ──────────────────────
if [[ -n "${JWT_SECRET_KEY:-}" ]]; then
    echo "✓ JWT_SECRET_KEY already set (from .env)."
else
    JWT_SECRET_KEY="$(generate_secret 32)"
    save_env_var "$ENV_FILE" "JWT_SECRET_KEY" "$JWT_SECRET_KEY"
    echo "✓ Generated JWT_SECRET_KEY (64 hex chars)"
fi
export JWT_SECRET_KEY

# ── Set CORS_ORIGINS to the panel domain if not set ─────────────────────────
if [[ -z "${CORS_ORIGINS:-}" ]]; then
    CORS_ORIGINS="https://${PANEL_DOMAIN}"
    save_env_var "$ENV_FILE" "CORS_ORIGINS" "$CORS_ORIGINS"
fi
export CORS_ORIGINS

echo ""
echo "✓ Configuration saved to $ENV_FILE"

# ── Build frontend (React SPA) ──────────────────────────────────────────────
echo "→ Building frontend (React SPA)..."
if [[ ! -d "$FRONTEND_DIST" ]] || [[ -z "$(ls -A "$FRONTEND_DIST" 2>/dev/null)" ]]; then
    echo "  frontend/dist not found. Building from source..."
    if command -v npm &>/dev/null; then
        (cd "$REPO_DIR/frontend" && npm ci && npm run build)
    else
        echo "ERROR: npm not found. Install Node.js or pre-build the frontend." >&2
        exit 1
    fi
fi

# Copy built frontend into the mgmt directory for Docker volume mount.
mkdir -p "$SCRIPT_DIR/frontend/dist"
cp -r "$FRONTEND_DIST/." "$SCRIPT_DIR/frontend/dist/"
echo "✓ Frontend built and copied to $SCRIPT_DIR/frontend/dist/"

# ── Generate Angie config from template ─────────────────────────────────────
echo "→ Generating Angie configuration..."
sed "s|__PANEL_DOMAIN__|${PANEL_DOMAIN}|g" "$ANGIE_TEMPLATE" > "$ANGIE_CONF"
echo "✓ Generated $ANGIE_CONF"

# ── Obtain Let's Encrypt certificate (AC5: HTTPS) ───────────────────────────
echo "→ Checking Let's Encrypt certificate..."
LE_DIR="$SCRIPT_DIR/letsencrypt"
CERT_DIR="$LE_DIR/live/${PANEL_DOMAIN}"
mkdir -p "$LE_DIR"

if [[ -f "$CERT_DIR/fullchain.pem" ]] && [[ -f "$CERT_DIR/privkey.pem" ]]; then
    echo "✓ Let's Encrypt certificate already exists for ${PANEL_DOMAIN}."
else
    echo "  No certificate found. Will obtain via certbot standalone."
    echo "  (Requires ports 80/443 to be free and DNS to point to this server.)"
    # Try certbot; if it fails, fall back to self-signed for initial testing.
    if command -v certbot &>/dev/null; then
        sudo certbot certonly --standalone \
            -d "$PANEL_DOMAIN" \
            --non-interactive --agree-tos \
            --register-unsafely-without-email \
            --config-dir "$LE_DIR" \
            --work-dir "$LE_DIR" \
            --logs-dir "$LE_DIR/logs" \
            2>/dev/null || {
            echo "⚠  certbot failed. Using self-signed certificate for now."
            echo "  Run 'certbot certonly --standalone -d ${PANEL_DOMAIN}' manually."
            _generate_self_signed "$PANEL_DOMAIN" "$CERT_DIR"
        }
    else
        echo "⚠  certbot not installed. Using self-signed certificate."
        echo "  Install certbot for proper Let's Encrypt TLS."
        _generate_self_signed "$PANEL_DOMAIN" "$CERT_DIR"
    fi
fi

echo "✓ Certificate configured."

# ── Deploy with Docker Compose ──────────────────────────────────────────────
echo "→ Starting containers via Docker Compose..."
cd "$SCRIPT_DIR"

if docker compose version &>/dev/null 2>&1; then
    docker compose down 2>/dev/null || true
    docker compose up -d --build
else
    docker-compose down 2>/dev/null || true
    docker-compose up -d --build
fi

# ── Post-deploy summary ─────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ Management server deployed successfully!                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Panel:       https://${PANEL_DOMAIN}"
echo "  API:         https://${PANEL_DOMAIN}/api"
echo "  Admin user:  ${ADMIN_USERNAME}"
echo ""
echo "  ── Services ────────────────────────────────────────────────────"
echo "  api+bot:     telemt-mgmt-api  (FastAPI :8000 + bot long polling)"
echo "  frontend:    telemt-mgmt-frontend (Angie :80/:443)"
echo "  postgres:    telemt-mgmt-db  (postgres:16-alpine)"
echo ""
echo "  ── Next steps ─────────────────────────────────────────────────"
echo "  1. Verify panel: https://${PANEL_DOMAIN}"
echo "  2. Login with admin credentials."
echo "  3. Verify bot is polling: docker logs telemt-mgmt-api"
echo ""
echo "  Re-run this script to update configuration (idempotent)."
echo ""
