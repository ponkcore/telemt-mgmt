#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy-exit.sh — deploy telemt + Xray-exit + Angie on the EU exit server.
#
# Installs telemt (MTProto/FakeTLS proxy on :8443), Xray-exit (VLESS-Reality
# inbound on :443, terminates encrypted S2 tunnel from entry server), and
# Angie (mask host on :8080) via Docker Compose. Configures firewall rules,
# generates config.toml and xray-config.json from operator inputs.
#
# Per ADR-009@0.2.0 / ARCH-001@0.2.0 §3 C7:
#   - Xray-exit generates its own X25519 keypair and VLESS UUID
#   - The public key and UUID are output for the operator to enter in
#     deploy-entry.sh on the entry server
#   - telemt moves from :443 to :8443 (Xray owns :443 on exit)
#
# Prompts for:
#   DOMAIN          — exit server domain (e.g. proxy.example.com)
#   AD_TAG          — Telegram ad_tag from @MTProxybot
#   TLS_DOMAIN      — FakeTLS camouflage domain (recommended: github.com)
#   TELEMT_SECRET   — telemt secret (auto-generate option)
#   MANAGEMENT_IPS  — IPs allowed to access :9091 API
#   MONITORING_IPS  — IPs allowed to access :9090 Prometheus metrics
#
# Auto-generates (stored in .env — INV-SECRETS):
#   EXIT_VLESS_UUID          — VLESS UUID for exit Xray inbound (AC10)
#   EXIT_REALITY_PRIVATE_KEY — X25519 private key for exit Xray Reality (AC9)
#   EXIT_REALITY_PUBLIC_KEY  — X25519 public key (output for entry server)
#   EXIT_REALITY_SNI         — SNI for exit Reality (default: www.microsoft.com)
#   EXIT_REALITY_SHORT_IDS   — Comma-separated short IDs for exit Reality
#   AUTH_HEADER              — telemt API auth header
#
# Idempotent: on re-run, reads existing .env and skips prompts (INV-IDEMPOTENT).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Timing wrapper ───────────────────────────────────────────────────────────
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
XRAY_TEMPLATE="$SCRIPT_DIR/xray-config.json.template"
XRAY_CONFIG="$SCRIPT_DIR/xray-config.json"

# ── Pre-flight ──────────────────────────────────────────────────────────────
check_docker

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  telemt-mgmt — Exit Server Deploy (telemt + Xray + Angie)    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Load existing config (idempotent re-run detection) ──────────────────────
# INV-IDEMPOTENT: load_env sources .env if it exists; prompt_for skips prompts
# when the variable is already set (AC14).
load_env "$ENV_FILE"

# ── Prompt for configuration ────────────────────────────────────────────────

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
# Check if already set from .env (re-run detection — INV-IDEMPOTENT).
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

# ── Exit Xray VLESS-Reality keypair generation (AC9) ────────────────────────
# Generate X25519 keypair for exit Xray Reality (reuses the pattern from
# deploy-entry.sh). On re-run, existing values from .env are used (INV-IDEMPOTENT).
if [[ -n "${EXIT_REALITY_PRIVATE_KEY:-}" ]]; then
    echo "✓ EXIT_REALITY_PRIVATE_KEY already set (from .env)."
else
    echo ""
    echo "Exit Xray Reality keypair generation (AC9):"
    echo "  Generating X25519 keypair for exit server's VLESS-Reality inbound."
    printf "Auto-generate X25519 keypair? [Y/n]: "
    read -r exit_auto_key
    exit_auto_key="${exit_auto_key:-Y}"
    if [[ "${exit_auto_key,,}" == "y" ]]; then
        echo "→ Generating X25519 keypair via xray x25519..."
        if command -v xray &>/dev/null; then
            EXIT_KEYPAIR=$(xray x25519)
        else
            echo "  xray binary not found locally, using Docker..."
            EXIT_KEYPAIR=$(docker run --rm ghcr.io/xtls/xray-core:latest xray x25519)
        fi
        EXIT_REALITY_PRIVATE_KEY=$(echo "$EXIT_KEYPAIR" | grep -i "Private" | awk '{print $NF}')
        EXIT_REALITY_PUBLIC_KEY=$(echo "$EXIT_KEYPAIR" | grep -i "Public" | awk '{print $NF}')
        echo "✓ Generated exit private key: ${EXIT_REALITY_PRIVATE_KEY:0:8}...(truncated)"
        echo "  Exit public key (enter in deploy-entry.sh): $EXIT_REALITY_PUBLIC_KEY"
    else
        printf "Enter exit Reality private key (X25519): "
        read -r EXIT_REALITY_PRIVATE_KEY
        if [[ -z "$EXIT_REALITY_PRIVATE_KEY" ]]; then
            echo "ERROR: EXIT_REALITY_PRIVATE_KEY is required." >&2
            exit 1
        fi
        printf "Enter exit Reality public key (X25519): "
        read -r EXIT_REALITY_PUBLIC_KEY
        if [[ -z "$EXIT_REALITY_PUBLIC_KEY" ]]; then
            echo "ERROR: EXIT_REALITY_PUBLIC_KEY is required." >&2
            exit 1
        fi
    fi
    export EXIT_REALITY_PRIVATE_KEY
    export EXIT_REALITY_PUBLIC_KEY
fi
save_env_var "$ENV_FILE" "EXIT_REALITY_PRIVATE_KEY" "$EXIT_REALITY_PRIVATE_KEY"
save_env_var "$ENV_FILE" "EXIT_REALITY_PUBLIC_KEY" "$EXIT_REALITY_PUBLIC_KEY"

# ── Exit VLESS UUID generation (AC10) ───────────────────────────────────────
# Generate VLESS UUID for exit Xray inbound. On re-run, existing value is used.
if [[ -n "${EXIT_VLESS_UUID:-}" ]]; then
    echo "✓ EXIT_VLESS_UUID already set (from .env)."
else
    echo ""
    echo "Exit VLESS UUID generation (AC10):"
    printf "Auto-generate VLESS UUID? [Y/n]: "
    read -r exit_auto_uuid
    exit_auto_uuid="${exit_auto_uuid:-Y}"
    if [[ "${exit_auto_uuid,,}" == "y" ]]; then
        echo "→ Generating VLESS UUID..."
        if command -v xray &>/dev/null; then
            EXIT_VLESS_UUID=$(xray uuid)
        elif command -v uuidgen &>/dev/null; then
            EXIT_VLESS_UUID=$(uuidgen)
        else
            echo "  xray and uuidgen not found, using Docker..."
            EXIT_VLESS_UUID=$(docker run --rm ghcr.io/xtls/xray-core:latest xray uuid)
        fi
        echo "✓ Generated VLESS UUID: $EXIT_VLESS_UUID"
    else
        printf "Enter VLESS UUID for exit Xray: "
        read -r EXIT_VLESS_UUID
        if [[ -z "$EXIT_VLESS_UUID" ]]; then
            echo "ERROR: EXIT_VLESS_UUID is required." >&2
            exit 1
        fi
    fi
    export EXIT_VLESS_UUID
fi
save_env_var "$ENV_FILE" "EXIT_VLESS_UUID" "$EXIT_VLESS_UUID"

# ── Exit Reality SNI and short IDs ──────────────────────────────────────────
# EXIT_REALITY_SNI — SNI for the exit server's Reality.
# Default: www.microsoft.com (TKT-019 self-steal is deferred; this is safe).
if [[ -n "${EXIT_REALITY_SNI:-}" ]]; then
    echo "✓ EXIT_REALITY_SNI already set (from .env): $EXIT_REALITY_SNI"
else
    EXIT_REALITY_SNI="$(prompt_for "EXIT_REALITY_SNI" \
        "Enter exit Reality SNI (default: www.microsoft.com)" \
        "www.microsoft.com")"
fi
save_env_var "$ENV_FILE" "EXIT_REALITY_SNI" "$EXIT_REALITY_SNI"

# EXIT_REALITY_SHORT_IDS — auto-generate if not provided.
if [[ -n "${EXIT_REALITY_SHORT_IDS:-}" ]]; then
    echo "✓ EXIT_REALITY_SHORT_IDS already set (from .env)."
else
    echo ""
    echo "Exit Reality short IDs:"
    printf "Auto-generate exit Reality short IDs? [Y/n]: "
    read -r exit_auto_ids
    exit_auto_ids="${exit_auto_ids:-Y}"
    if [[ "${exit_auto_ids,,}" == "y" ]]; then
        echo "→ Generating short IDs..."
        EXIT_REALITY_SHORT_IDS=$(generate_secret 4)
        local_exit_short_id=$(generate_secret 4)
        EXIT_REALITY_SHORT_IDS="${EXIT_REALITY_SHORT_IDS},${local_exit_short_id}"
        echo "✓ Generated short IDs: $EXIT_REALITY_SHORT_IDS"
    else
        printf "Enter exit Reality short IDs (comma-separated hex, e.g. ab12cd34): "
        read -r EXIT_REALITY_SHORT_IDS
        if [[ -z "$EXIT_REALITY_SHORT_IDS" ]]; then
            echo "ERROR: EXIT_REALITY_SHORT_IDS is required." >&2
            exit 1
        fi
    fi
    export EXIT_REALITY_SHORT_IDS
fi
save_env_var "$ENV_FILE" "EXIT_REALITY_SHORT_IDS" "$EXIT_REALITY_SHORT_IDS"

echo ""
echo "✓ Exit Xray configuration saved to $ENV_FILE"

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

# ── Generate xray-config.json from template (AC13) ──────────────────────────
echo "→ Generating xray-config.json from template..."

# Format EXIT_REALITY_SHORT_IDS as a JSON array body: "id1", "id2"
EXIT_REALITY_SHORT_IDS_JSON=$(echo "$EXIT_REALITY_SHORT_IDS" | sed 's/,/", "/g; s/^/"/; s/$/"/')

sed \
    -e "s|__EXIT_VLESS_UUID__|${EXIT_VLESS_UUID}|g" \
    -e "s|__EXIT_REALITY_PRIVATE_KEY__|${EXIT_REALITY_PRIVATE_KEY}|g" \
    -e "s|__EXIT_REALITY_SNI__|${EXIT_REALITY_SNI}|g" \
    -e "s|__EXIT_REALITY_SHORT_IDS_JSON__|${EXIT_REALITY_SHORT_IDS_JSON}|g" \
    "$XRAY_TEMPLATE" > "$XRAY_CONFIG"

echo "✓ Generated $XRAY_CONFIG"

# ── Generate Angie config from template ──────────────────────────────────────
echo "→ Generating Angie configuration..."
cp "$ANGIE_TEMPLATE" "$ANGIE_CONF"
echo "✓ Generated $ANGIE_CONF"

# ── System limits (ulimit) ───────────────────────────────────────────────────
echo "→ Setting file descriptor limit (ulimit -n 65536)..."
ulimit -n 65536 2>/dev/null || true
echo "✓ ulimit set"

# ── Firewall rules ───────────────────────────────────────────────────────────
echo "→ Configuring firewall rules (UFW)..."

if command -v ufw &>/dev/null; then
    # Allow SSH (don't lock ourselves out).
    sudo ufw allow ssh 2>/dev/null || true

    # Allow :443/tcp for Xray-exit VLESS-Reality inbound (from entry server).
    sudo ufw allow 443/tcp 2>/dev/null || true

    # Allow :8080/tcp for Angie mask host.
    sudo ufw allow 8080/tcp 2>/dev/null || true

    # Restrict :9090 (Prometheus metrics) to monitoring IPs only.
    if [[ -n "$MONITORING_IPS" ]]; then
        # Remove existing :9090 rules, then re-add for monitoring IPs.
        sudo ufw delete allow 9090/tcp 2>/dev/null || true
        IFS=',' read -ra _mon_ips <<< "$MONITORING_IPS"
        for _ip in "${_mon_ips[@]}"; do
            _ip="${_ip//[[:space:]]/}"
            [[ -n "$_ip" ]] && sudo ufw allow from "$_ip" to any port 9090 proto tcp 2>/dev/null || true
        done
    fi

    # Restrict :9091 (telemt API) to management IPs only.
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
    echo "   Manually configure: ufw allow 443/tcp (Xray), ufw allow 8080/tcp (Angie), restrict 9090/9091."
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
echo "  Domain:          $DOMAIN"
echo "  TLS domain:      $TLS_DOMAIN"
echo "  ad_tag:          $AD_TAG"
echo "  Mask host:       http://$DOMAIN:8080"
echo "  Encrypted S2:    VLESS-Reality inbound on :443 (from entry server)"
echo "  telemt port:     :8443 (internal, forwarded from Xray-exit)"
echo ""
echo "  ── Entry server configuration (copy to deploy-entry.sh) ──────"
echo "  EXIT_VLESS_UUID:     $EXIT_VLESS_UUID"
echo "  EXIT_PUBLIC_KEY:     $EXIT_REALITY_PUBLIC_KEY"
echo "  EXIT_REALITY_SNI:    $EXIT_REALITY_SNI"
echo "  EXIT_SHORT_ID:       $(echo "$EXIT_REALITY_SHORT_IDS" | cut -d, -f1)"
echo ""
echo "  ── Next steps ─────────────────────────────────────────────────"
echo "  ad_tag configured. Verify promotion at @MTProxybot /myproxies"
echo "  to confirm your proxy is being promoted in Telegram."
echo "  Run deploy-entry.sh on the entry server with the values above."
echo ""
echo "  Re-run this script to update configuration (idempotent)."
echo ""
