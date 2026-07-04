#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy-landing.sh — deploy the telemt-mgmt one-pager landing page.
#
# Installs Angie via Docker Compose to serve a static HTML page with a
# "Получить прокси" button linking to a Telegram bot.
#
# Prompts for:
#   BOT_URL  — Telegram bot URL (t.me/botname)
#   DOMAIN   — domain for HTTPS (optional; empty = HTTP-only)
#
# Idempotent: on re-run, reads existing .env and skips prompts (INV-IDEMPOTENT).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve script directory (handles symlinks)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source shared helpers
# shellcheck disable=SC1091
source "$INFRA_DIR/lib/common.sh"

# ── Paths ───────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
HTML_SOURCE="$SCRIPT_DIR/html/index.html"
HTML_DEPLOYED="$SCRIPT_DIR/html/index.deployed.html"
ANGIE_TEMPLATE="$SCRIPT_DIR/angie.conf.template"
ANGIE_CONF="$SCRIPT_DIR/angie.conf"
CERT_DIR="$SCRIPT_DIR/certs"

# ── Pre-flight ──────────────────────────────────────────────────────────────
check_docker

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  telemt-mgmt — Landing Page Deploy                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Load existing config (idempotent re-run detection) ──────────────────────
load_env "$ENV_FILE"

# ── Prompt for configuration ────────────────────────────────────────────────
BOT_URL="$(prompt_for "BOT_URL" "Enter Telegram bot URL (e.g. https://t.me/myproxybot)")"
save_env_var "$ENV_FILE" "BOT_URL" "$BOT_URL"

# DOMAIN is optional — prompt_for fatal-errors on empty input, so handle manually.
# On re-run, DOMAIN is already loaded from .env (even if empty).
if [[ -n "${DOMAIN:-}" ]]; then
    # Already set from .env — use as-is.
    :
elif [[ -v DOMAIN ]]; then
    # DOMAIN is set but empty (e.g. DOMAIN= in .env) — keep as empty (HTTP-only).
    :
else
    printf "Enter domain for HTTPS (leave empty for HTTP-only): "
    read -r DOMAIN
fi
save_env_var "$ENV_FILE" "DOMAIN" "${DOMAIN:-}"

echo ""
echo "✓ Configuration saved to $ENV_FILE"

# ── Generate deployed HTML (replace __BOT_URL__ placeholder) ────────────────
echo "→ Generating index.deployed.html with bot URL: $BOT_URL"
sed "s|__BOT_URL__|$BOT_URL|g" "$HTML_SOURCE" > "$HTML_DEPLOYED"
echo "✓ Generated $HTML_DEPLOYED"

# ── Generate Angie config from template ─────────────────────────────────────
echo "→ Generating Angie configuration"

# Determine server_name and TLS settings
if [[ -n "$DOMAIN" ]]; then
    SERVER_NAME="$DOMAIN"
    TLS_ENABLED="yes"
    CERT_PATH="/etc/angie/certs/fullchain.pem"
    KEY_PATH="/etc/angie/certs/privkey.pem"
else
    SERVER_NAME="_"
    TLS_ENABLED="no"
    CERT_PATH=""
    KEY_PATH=""
fi

# Build the TLS server block (or empty comment if no TLS)
TLS_BLOCK=""
if [[ "$TLS_ENABLED" == "yes" ]]; then
    TLS_BLOCK=$(cat <<'TLSBLOCK'
    server {
        listen 443 ssl;
        listen [::]:443 ssl;
        http2 on;
        server_name __DOMAIN__;

        ssl_certificate     __CERT_PATH__;
        ssl_certificate_key __KEY_PATH__;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;
        ssl_session_cache   shared:SSL:2m;
        ssl_session_timeout 1h;

        root /var/www/html;
        index index.deployed.html;

        location / {
            try_files $uri $uri/ =404;
        }
    }
TLSBLOCK
    )
    # Substitute placeholders in the TLS block
    TLS_BLOCK="${TLS_BLOCK//__DOMAIN__/$SERVER_NAME}"
    TLS_BLOCK="${TLS_BLOCK//__CERT_PATH__/$CERT_PATH}"
    TLS_BLOCK="${TLS_BLOCK//__KEY_PATH__/$KEY_PATH}"
else
    TLS_BLOCK="# TLS disabled — HTTP only"
fi

# Process the template: substitute placeholders and inject TLS block
# First, replace domain placeholder
sed "s|__DOMAIN__|$SERVER_NAME|g" "$ANGIE_TEMPLATE" \
    | sed "s|__TLS_ENABLED__|$TLS_ENABLED|g" \
    | sed "s|__CERT_PATH__|$CERT_PATH|g" \
    | sed "s|__KEY_PATH__|$KEY_PATH|g" \
    | awk -v tls="$TLS_BLOCK" '{gsub(/#__TLS_BLOCK__/, tls); print}' \
    > "$ANGIE_CONF"

echo "✓ Generated $ANGIE_CONF"

# ── HTTPS / Let's Encrypt ───────────────────────────────────────────────────
if [[ -n "$DOMAIN" ]]; then
    mkdir -p "$CERT_DIR"
    echo "→ Checking for TLS certificates for $DOMAIN"
    if [[ ! -f "$CERT_DIR/fullchain.pem" || ! -f "$CERT_DIR/privkey.pem" ]]; then
        echo "  Certificates not found. Obtaining via Let's Encrypt (certbot)..."
        if ! command -v certbot &>/dev/null; then
            echo "  certbot not installed. Installing via snap/apt..."
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq && sudo apt-get install -y -qq certbot
            else
                echo "  ERROR: Cannot install certbot automatically. Please install it manually." >&2
                echo "  Then re-run this script." >&2
                exit 1
            fi
        fi
        sudo certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email
        # Copy certs to the local certs directory (Docker mounts it read-only)
        sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_DIR/fullchain.pem"
        sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$CERT_DIR/privkey.pem"
        sudo chown -R "$(id -u):$(id -g)" "$CERT_DIR"
        echo "✓ TLS certificates obtained"
    else
        echo "✓ TLS certificates already present"
    fi
else
    echo "→ No domain specified — HTTP only (port 80)"
fi

# ── Deploy with Docker Compose ──────────────────────────────────────────────
echo "→ Starting Angie container via Docker Compose..."
cd "$SCRIPT_DIR"


if docker compose version &>/dev/null 2>&1; then
    docker compose down 2>/dev/null || true
    docker compose up -d
else
    docker-compose down 2>/dev/null || true
    docker-compose up -d
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ Landing page deployed successfully!                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
if [[ -n "$DOMAIN" ]]; then
    echo "  URL:  https://$DOMAIN"
else
    echo "  URL:  http://localhost"
fi
echo "  Bot:  $BOT_URL"
echo ""
echo "  Re-run this script to update configuration."
echo ""
