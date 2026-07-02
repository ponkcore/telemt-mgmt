#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy-exit.sh — deploy telemt + Angie on the EU exit server.
#
# Installs telemt (MTProto/FakeTLS proxy) and Angie (mask host) via Docker
# Compose. Configures firewall rules, generates config.toml from operator
# inputs, and outputs a post-deploy message about ad_tag verification.
#
# Prompts for:
#   DOMAIN         — exit server domain (e.g. proxy.example.com)
#   AD_TAG         — Telegram ad_tag from @MTProxybot
#   TLS_DOMAIN     — FakeTLS camouflage domain (recommended: github.com)
#   TELEMT_SECRET  — telemt secret (auto-generate option)
#   MANAGEMENT_IPS — IPs allowed to access :9091 API
#   MONITORING_IPS — IPs allowed to access :9090 Prometheus metrics
#
# Idempotent: on re-run, reads existing .env and skips prompts (INV-IDEMPOTENT).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Timing wrapper (AC12) ────────────────────────────────────────────────────
_DEPLOY_START_TIME=$(date +%s)

# Print elapsed time on exit (success or failure).
_finish_timer() {
    local end_time elapsed
    end_time=$(date +%s)
    elapsed=$((end_time - _DEPLOY_START_TIME))
    echo ""
    echo "⏱  Total elapsed time: ${elapsed}s"
}
trap _finish_timer EXIT

# Resolve script directory (handles symlinks)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source shared helpers
# shellcheck disable=SC1091
source "$INFRA_DIR/lib/common.sh"

# ── Paths ───────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
CONFIG_TEMPLATE="$SCRIPT_DIR/config.toml.template"
CONFIG_DIR="$SCRIPT_DIR/config"
CONFIG_FILE="$CONFIG_DIR/config.toml"
ANGIE_TEMPLATE="$SCRIPT_DIR/angie.conf.template"
ANGIE_CONF="$SCRIPT_DIR/angie.conf"

# ── Pre-flight ──────────────────────────────────────────────────────────────
check_docker

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  telemt-mgmt — Exit Server Deploy (telemt + Angie)           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Load existing config (idempotent re-run detection) ──────────────────────
# INV-IDEMPOTENT: load_env sources .env if it exists; prompt_for skips prompts
# when the variable is already set (AC1).
load_env "$ENV_FILE"

# ── Prompt for configuration (AC2) ──────────────────────────────────────────

# DOMAIN — exit server domain
DOMAIN="$(prompt_for "DOMAIN" "Enter exit server domain (e.g. proxy.example.com)")"
save_env_var "$ENV_FILE" "DOMAIN" "$DOMAIN"

# AD_TAG — Telegram ad_tag from @MTProxybot
AD_TAG="$(prompt_for "AD_TAG" "Enter ad_tag from @MTProxybot (32-char hex)")"
save_env_var "$ENV_FILE" "AD_TAG" "$AD_TAG"

# TLS_DOMAIN — FakeTLS camouflage domain (with recommendations)
TLS_DOMAIN="$(prompt_for "TLS_DOMAIN" \
    "Enter FakeTLS domain (recommended: github.com primary, www.microsoft.com backup)" \
    "github.com")"
save_env_var "$ENV_FILE" "TLS_DOMAIN" "$TLS_DOMAIN"

# TELEMT_SECRET — auto-generate option
# Check if already set from .env (re-run detection).
if [[ -n "${TELEMT_SECRET:-}" ]]; then
    echo "✓ TELEMT_SECRET already set (from .env)."
else
    printf "Generate telemt secret automatically? [Y/n]: "
    read -r gen_secret
    gen_secret="${gen_secret:-Y}"
    if [[ "${gen_secret,,}" == "y" || "${gen_secret,,}" == "yes" ]]; then
        TELEMT_SECRET="$(generate_secret 32)"
        echo "✓ Generated TELEMT_SECRET (64 hex chars)"
    else
        printf "Enter telemt secret: "
        read -r TELEMT_SECRET
        if [[ -z "$TELEMT_SECRET" ]]; then
            echo "ERROR: TELEMT_SECRET is required." >&2
            exit 1
        fi
    fi
fi
export TELEMT_SECRET
save_env_var "$ENV_FILE" "TELEMT_SECRET" "$TELEMT_SECRET"

# MANAGEMENT_IPS — IPs allowed to access :9091 API
MANAGEMENT_IPS="$(prompt_for "MANAGEMENT_IPS" \
    "Enter management server IPs (comma-separated, e.g. 10.0.0.5,203.0.113.10)")"
save_env_var "$ENV_FILE" "MANAGEMENT_IPS" "$MANAGEMENT_IPS"

# MONITORING_IPS — IPs allowed to access :9090 Prometheus metrics
MONITORING_IPS="$(prompt_for "MONITORING_IPS" \
    "Enter monitoring server IPs (comma-separated, e.g. 10.0.0.8,198.51.100.20)")"
save_env_var "$ENV_FILE" "MONITORING_IPS" "$MONITORING_IPS"

echo ""
echo "✓ Configuration saved to $ENV_FILE"

# ── Generate auth_header (for telemt API) ────────────────────────────────────
if [[ -n "${AUTH_HEADER:-}" ]]; then
    echo "✓ AUTH_HEADER already set (from .env)."
else
    AUTH_HEADER="$(generate_secret 32)"
    echo "✓ Generated AUTH_HEADER (64 hex chars)"
fi
export AUTH_HEADER
save_env_var "$ENV_FILE" "AUTH_HEADER" "$AUTH_HEADER"

# ── Generate config.toml from template ───────────────────────────────────────
echo "→ Generating config.toml from template..."

mkdir -p "$CONFIG_DIR"

# Build the whitelist array for TOML: "ip1/32", "ip2/32"
# Convert comma-separated IPs to TOML-quoted, CIDR-suffixed entries.
MANAGEMENT_IPS_TOML=""
if [[ -n "$MANAGEMENT_IPS" ]]; then
    # Split on commas, quote each as CIDR /32, join with ", "
    IFS=',' read -ra _ips <<< "$MANAGEMENT_IPS"
    _first=1
    for _ip in "${_ips[@]}"; do
        _ip="${_ip//[[:space:]]/}"  # trim whitespace
        if [[ -n "$_ip" ]]; then
            if [[ $_first -eq 0 ]]; then
                MANAGEMENT_IPS_TOML+=", "
            fi
            MANAGEMENT_IPS_TOML+="\"${_ip}/32\""
            _first=0
        fi
    done
fi
# Always include localhost in the whitelist.
if [[ -n "$MANAGEMENT_IPS_TOML" ]]; then
    MANAGEMENT_IPS_TOML+=", "
fi
MANAGEMENT_IPS_TOML+="\"127.0.0.1/32\", \"::1/128\""

sed \
    -e "s|__AD_TAG__|${AD_TAG}|g" \
    -e "s|__TELEMT_SECRET__|${TELEMT_SECRET}|g" \
    -e "s|__TLS_DOMAIN__|${TLS_DOMAIN}|g" \
    -e "s|__AUTH_HEADER__|${AUTH_HEADER}|g" \
    -e "s|__MANAGEMENT_IPS__|${MANAGEMENT_IPS_TOML}|g" \
    "$CONFIG_TEMPLATE" > "$CONFIG_FILE"

echo "✓ Generated $CONFIG_FILE"

# ── Generate Angie config from template ──────────────────────────────────────
echo "→ Generating Angie configuration..."
cp "$ANGIE_TEMPLATE" "$ANGIE_CONF"
echo "✓ Generated $ANGIE_CONF"

# ── System limits (ulimit) ───────────────────────────────────────────────────
echo "→ Setting file descriptor limit (ulimit -n 65536)..."
ulimit -n 65536 2>/dev/null || true
echo "✓ ulimit set"

# ── Firewall rules (AC7) ─────────────────────────────────────────────────────
echo "→ Configuring firewall rules (UFW)..."

if command -v ufw &>/dev/null; then
    # Allow SSH (don't lock ourselves out).
    sudo ufw allow ssh 2>/dev/null || true

    # Allow :443/tcp for telemt MTProto/FakeTLS.
    sudo ufw allow 443/tcp 2>/dev/null || true

    # Allow :8080/tcp for Angie mask host.
    sudo ufw allow 8080/tcp 2>/dev/null || true

    # Restrict :9090 (Prometheus metrics) to monitoring IPs only (AC7).
    if [[ -n "$MONITORING_IPS" ]]; then
        # Remove existing :9090 rules, then re-add for monitoring IPs.
        sudo ufw delete allow 9090/tcp 2>/dev/null || true
        IFS=',' read -ra _mon_ips <<< "$MONITORING_IPS"
        for _ip in "${_mon_ips[@]}"; do
            _ip="${_ip//[[:space:]]/}"
            [[ -n "$_ip" ]] && sudo ufw allow from "$_ip" to any port 9090 proto tcp 2>/dev/null || true
        done
    fi

    # Restrict :9091 (telemt API) to management IPs only (AC7).
    if [[ -n "$MANAGEMENT_IPS" ]]; then
        sudo ufw delete allow 9091/tcp 2>/dev/null || true
        IFS=',' read -ra _mgmt_ips <<< "$MANAGEMENT_IPS"
        for _ip in "${_mgmt_ips[@]}"; do
            _ip="${_ip//[[:space:]]/}"
            [[ -n "$_ip" ]] && sudo ufw allow from "$_ip" to any port 9091 proto tcp 2>/dev/null || true
        done
    fi

    # Allow localhost for metrics and API.
    sudo ufw allow from 127.0.0.1 to any port 9090 proto tcp 2>/dev/null || true
    sudo ufw allow from 127.0.0.1 to any port 9091 proto tcp 2>/dev/null || true

    echo "✓ Firewall rules configured"
else
    echo "⚠  UFW not installed. Skipping firewall configuration."
    echo "   Manually configure: ufw allow 443/tcp, restrict 9090/9091 to mgmt/monitoring IPs."
fi

# ── Deploy with Docker Compose ──────────────────────────────────────────────
echo "→ Starting containers via Docker Compose..."
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
echo "║  ✓ Exit server deployed successfully!                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Domain:     $DOMAIN"
echo "  TLS domain: $TLS_DOMAIN"
echo "  ad_tag:     $AD_TAG"
echo "  Mask host:  http://$DOMAIN:8080"
echo ""
echo "  ── Next steps (AC11) ─────────────────────────────────────────"
echo "  ad_tag configured. Verify promotion at @MTProxybot /myproxies"
echo "  to confirm your proxy is being promoted in Telegram."
echo ""
echo "  Re-run this script to update configuration (idempotent)."
echo ""
