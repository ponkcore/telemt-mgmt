#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy-exit.sh — deploy telemt + Xray-exit + Angie on the EU exit server.
#
# Installs telemt (MTProto/FakeTLS proxy on :8443), Xray-exit (VLESS-Reality
# inbound on :443, terminates encrypted S2 tunnel from entry server), and
# Angie (mask host on :8080, or TLS server on :443 for self-steal) via Docker
# Compose. Configures firewall rules, generates config.toml and xray-config.json
# from operator inputs.
#
# Per ADR-009@0.2.0 / ARCH-001@0.2.0 §3 C7:
#   - Xray-exit generates its own X25519 keypair and VLESS UUID
#   - The public key and UUID are output for the operator to enter in
#     deploy-entry.sh on the entry server
#   - telemt moves from :443 to :8443 (Xray owns :443 on exit)
#
# Per ADR-010@0.2.0 (self-steal domain support):
#   - If TLS_DOMAIN is not in the known third-party list, it is treated as a
#     self-steal domain (operator's own domain with DNS pointing to this server)
#   - Self-steal mode: mask_port=443, Angie serves TLS cert on :443 via
#     angie-selsteal.conf.template, Let's Encrypt cert obtained via certbot
#   - Third-party mode (default): mask_port=443, tls_emulation fetches from real domain on :443
#   - Default third-party domain changed from github.com to www.microsoft.com
#
# ── Known operational issues (TKT-025 B4/B5 deploy experience docs) ────────
#
# B4: socat workaround for :9090/:9091 PROXYv2 reset (Medium severity)
#   telemt's `proxy_protocol = true` in [server] applies to ALL listeners,
#   including the metrics (:9090) and API (:9091) HTTP endpoints. External
#   HTTP clients (Prometheus scraper, curl) cannot speak PROXYv2, so telemt
#   resets their connections — :9090 and :9091 are unreachable directly.
#
#   Workaround: run socat TCP proxies on the exit server that strip the
#   PROXYv2 header before forwarding to localhost:9090/9091:
#     :9093 → localhost:9090  (metrics — for Prometheus scraper)
#     :9094 → localhost:9091  (API — for management server)
#
#   Create two systemd services:
#     /etc/systemd/system/telemt-metrics-proxy.service:
#       ExecStart=/usr/bin/socat TCP-LISTEN:127.0.0.1:9093,reuseaddr,fork TCP:localhost:9090
#     /etc/systemd/system/telemt-api-proxy.service:
#       ExecStart=/usr/bin/socat TCP-LISTEN:127.0.0.1:9094,reuseaddr,fork TCP:localhost:9091
#
#   Then point Prometheus at :9093 and the management API client at :9094.
#   Install socat: apt-get install -y socat
#
#   NOTE: socat binds to 127.0.0.1 only — ports 9093/9094 are NOT exposed
#   publicly. If remote access is needed (e.g. Prometheus on another server),
#   restrict via UFW: ufw allow from <monitoring-ip> to any port 9093 proto tcp
#
# B5: self-steal domain is REQUIRED for tls_emulation (Blocker for tls_emulation)
#   telemt's rustls TLS client gets RST (connection reset) from ALL CDN-protected
#   third-party domains (Akamai, Google, Apple, GitHub, Microsoft) when fetching
#   the ServerHello for tls_emulation. curl (OpenSSL) works fine against the same
#   domains, but telemt's rustls does not. As a result, tls_emulation ALWAYS
#   falls back to a fake 2048-byte cert when using a third-party domain.
#
#   Self-steal is NOT optional for production tls_emulation — it is REQUIRED.
#   With a self-steal domain, telemt fetches the ServerHello from the local
#   Angie TLS server (operator-controlled LE cert), which always succeeds
#   because there is no CDN WAF in the path.
#
#   If you need tls_emulation=true (recommended for strongest TSPU evasion),
#   you MUST use a self-steal domain. Third-party domains will silently fail
#   tls_emulation and fall back to a fake cert.
#
# Prompts for:
#   DOMAIN          — exit server domain (e.g. proxy.example.com)
#   AD_TAG          — Telegram ad_tag from @MTProxybot
#   TLS_DOMAIN      — FakeTLS camouflage domain (default: www.microsoft.com,
#                     or operator's self-steal domain for production)
#   TELEMT_SECRET   — telemt secret (auto-generate option)
#   MANAGEMENT_IPS  — IPs allowed to access :9091 API
#   MONITORING_IPS  — IPs allowed to access :9090 Prometheus metrics
#
# Auto-generates (stored in .env — INV-SECRETS):
#   EXIT_VLESS_UUID          — VLESS UUID for exit Xray inbound (AC10)
#   EXIT_REALITY_PRIVATE_KEY — X25519 private key for exit Xray Reality (AC9)
#   EXIT_REALITY_PUBLIC_KEY  — X25519 public key (output for entry server)
#   EXIT_REALITY_SNI         — SNI for exit Reality (default: ads.x5.ru)
#   EXIT_REALITY_SHORT_IDS   — Comma-separated short IDs for exit Reality
#   AUTH_HEADER              — telemt API auth header
#   SELF_STEAL_DOMAIN        — set to TLS_DOMAIN when it's a self-steal domain
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
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source shared helpers
# shellcheck disable=SC1091
source "$INFRA_DIR/lib/common.sh"

# ── Paths ───────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
CONFIG_TEMPLATE="$SCRIPT_DIR/config.toml.template"
CONFIG_DIR="$SCRIPT_DIR/config"
CONFIG_FILE="$CONFIG_DIR/config.toml"
ANGIE_TEMPLATE="$SCRIPT_DIR/angie.conf.template"
ANGIE_SELSTEAL_TEMPLATE="$SCRIPT_DIR/angie-selsteal.conf.template"
ANGIE_CONF="$SCRIPT_DIR/angie.conf"
XRAY_TEMPLATE="$SCRIPT_DIR/xray-config.json.template"
XRAY_CONFIG="$SCRIPT_DIR/xray-config.json"

# ── Known third-party domains (AC2) ─────────────────────────────────────────
# If TLS_DOMAIN is NOT in this list, it is treated as a self-steal domain.
# Based on TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 top-10 FakeTLS candidates.
KNOWN_THIRD_PARTY_DOMAINS=(
    "www.microsoft.com"
    "www.apple.com"
    "dl.google.com"
    "storage.googleapis.com"
    "github.com"
    "www.twitch.tv"
    "www.netflix.com"
    "www.google.com"
    "registry.npmjs.org"
)

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

# TLS_DOMAIN — FakeTLS camouflage domain (AC1: default is www.microsoft.com)
# The default changed from github.com to www.microsoft.com per ADR-010@0.2.0:
# www.microsoft.com has no ASN mismatch risk that github.com carries (Azure vs
# Hetzner), and is a high-traffic stable TLS 1.3 domain.
# Operators can enter their own domain for self-steal (AC2).
TLS_DOMAIN="$(prompt_for "TLS_DOMAIN" \
    "Enter FakeTLS domain (default: www.microsoft.com, or your own domain for self-steal)" \
    "www.microsoft.com")"
save_env_var "$ENV_FILE" "TLS_DOMAIN" "$TLS_DOMAIN"

# ── Self-steal domain detection (AC2) ───────────────────────────────────────
# Check if TLS_DOMAIN is in the known third-party list. If NOT, treat it as a
# self-steal domain (operator's own domain with DNS A-record → this server).
SELF_STEAL_DOMAIN=""
_is_third_party=0
for _known in "${KNOWN_THIRD_PARTY_DOMAINS[@]}"; do
    if [[ "$TLS_DOMAIN" == "$_known" ]]; then
        _is_third_party=1
        break
    fi
done

if [[ $_is_third_party -eq 0 ]]; then
    # TLS_DOMAIN is not in the known third-party list → self-steal domain.
    SELF_STEAL_DOMAIN="$TLS_DOMAIN"
    export SELF_STEAL_DOMAIN
    save_env_var "$ENV_FILE" "SELF_STEAL_DOMAIN" "$SELF_STEAL_DOMAIN"
    echo ""
    echo "  ✓ Self-steal domain detected: $SELF_STEAL_DOMAIN"
    echo "    (not in known third-party list — treating as operator-owned domain)"
    echo "    Self-steal eliminates ASN mismatch (ADR-010@0.2.0)."

    # ── DNS verification prompt (AC3, INV-IDEMPOTENT) ──────────────────────
    # Before proceeding with cert acquisition, verify the operator has
    # configured the DNS A-record pointing to this server. certbot HTTP-01
    # challenge requires the domain to resolve to this server's IP.
    # On re-run, skip the prompt if DNS was already verified (stored in .env).
    if [[ "${SELF_STEAL_DNS_VERIFIED:-}" == "$SELF_STEAL_DOMAIN" ]]; then
        echo "  ✓ DNS already verified for $SELF_STEAL_DOMAIN (from .env)"
    else
        echo ""
        echo "  ⚠  DNS A-record requirement:"
        echo "    $SELF_STEAL_DOMAIN must have an A-record pointing to THIS server's IP."
        echo "    Configure it at your DNS provider (Cloudflare recommended, TTL=300)."
        echo "    The A-record must be DNS-only (grey cloud, not proxied) for certbot."

        _dns_verified=""
        while true; do
            printf "Have you configured DNS A-record for %s pointing to this server? (yes/no): " "$SELF_STEAL_DOMAIN"
            read -r _dns_verified
            _dns_verified="${_dns_verified,,}"
            if [[ "$_dns_verified" == "yes" || "$_dns_verified" == "y" ]]; then
                echo "  ✓ DNS verified by operator. Proceeding with cert acquisition."
                break
            elif [[ "$_dns_verified" == "no" || "$_dns_verified" == "n" ]]; then
                echo "  ✗ DNS A-record not configured. Self-steal requires DNS to be set up."
                echo "    Please configure the A-record at your DNS provider and re-run."
                echo "    Alternatively, use a third-party domain (www.microsoft.com)."
                exit 1
            else
                echo "  Please answer 'yes' or 'no'."
            fi
        done
        # Persist DNS verification so we skip this prompt on re-run (INV-IDEMPOTENT).
        save_env_var "$ENV_FILE" "SELF_STEAL_DNS_VERIFIED" "$SELF_STEAL_DOMAIN"
        export SELF_STEAL_DNS_VERIFIED="$SELF_STEAL_DOMAIN"
    fi

    # ── Let's Encrypt cert acquisition (§7 Constraints) ────────────────────
    # Obtain TLS certificate via certbot for the self-steal domain.
    # certbot uses HTTP-01 challenge: the domain must resolve to this server.
    # The cert is stored at /etc/letsencrypt/live/<domain>/.
    TLS_CERT_PATH="/etc/letsencrypt/live/${SELF_STEAL_DOMAIN}/fullchain.pem"
    TLS_KEY_PATH="/etc/letsencrypt/live/${SELF_STEAL_DOMAIN}/privkey.pem"

    if [[ -f "$TLS_CERT_PATH" && -f "$TLS_KEY_PATH" ]]; then
        echo "  ✓ Let's Encrypt cert already exists for $SELF_STEAL_DOMAIN"
        echo "    Cert: $TLS_CERT_PATH"
    else
        echo ""
        echo "  → Acquiring Let's Encrypt certificate for $SELF_STEAL_DOMAIN..."
        echo "    (certbot standalone HTTP-01 challenge — port 80 must be free)"

        # Install certbot if not present.
        if ! command -v certbot &>/dev/null; then
            echo "    Installing certbot..."
            sudo apt-get update -qq && sudo apt-get install -y -qq certbot
        fi

        # Stop any service on port 80 (certbot standalone needs it).
        sudo docker stop telemt-mask 2>/dev/null || true
        sudo systemctl stop nginx 2>/dev/null || true
        sudo systemctl stop angie 2>/dev/null || true

        # Run certbot certonly (standalone, non-interactive with --agree-tos).
        sudo certbot certonly --standalone \
            -d "$SELF_STEAL_DOMAIN" \
            --non-interactive \
            --agree-tos \
            --register-unsafely-without-email \
            --keep-until-expiring

        if [[ -f "$TLS_CERT_PATH" && -f "$TLS_KEY_PATH" ]]; then
            echo "  ✓ Let's Encrypt certificate acquired successfully."
            echo "    Cert: $TLS_CERT_PATH"
            echo "    Key:  $TLS_KEY_PATH"
            echo ""
            echo "  ⚠  Cert renewal is NOT automated. Add a cron job:"
            echo "    0 3 * * * certbot renew && docker restart telemt-mask"
            echo "    (Renewal runs daily at 3am; cert renews at 30 days before expiry)"
        else
            echo "  ✗ ERROR: certbot did not produce expected cert files." >&2
            echo "    Check that DNS A-record for $SELF_STEAL_DOMAIN resolves to this server." >&2
            echo "    You can re-run this script after fixing DNS." >&2
            exit 1
        fi
    fi

    # Copy certs into ./mask/certs/ so the Angie container can read them
    # via the existing ./mask:/var/www/mask:ro volume mount (F-H2 fix).
    CERTS_DIR="$SCRIPT_DIR/mask/certs"
    mkdir -p "$CERTS_DIR"
    sudo cp "$TLS_CERT_PATH" "$CERTS_DIR/fullchain.pem" 2>/dev/null || true
    sudo cp "$TLS_KEY_PATH" "$CERTS_DIR/privkey.pem" 2>/dev/null || true
    sudo chmod 644 "$CERTS_DIR/fullchain.pem" "$CERTS_DIR/privkey.pem" 2>/dev/null || true
    TLS_CERT_PATH="/var/www/mask/certs/fullchain.pem"
    TLS_KEY_PATH="/var/www/mask/certs/privkey.pem"

    # Save cert paths for reference.
    save_env_var "$ENV_FILE" "TLS_CERT_PATH" "$TLS_CERT_PATH"
    save_env_var "$ENV_FILE" "TLS_KEY_PATH" "$TLS_KEY_PATH"

    # Set mask_host and mask_port for self-steal mode (AC5).
    MASK_HOST="$SELF_STEAL_DOMAIN"
    MASK_PORT=443

    # Warn about port conflict if Xray-exit is also on :443.
    echo ""
    echo "  ⚠  Port conflict warning:"
    echo "    Self-steal mode uses Angie on :443 for TLS cert serving."
    echo "    Xray-exit (encrypted S2, ADR-009@0.2.0) also uses :443."
    echo "    If both are active, use SNI routing (angie-sni-router.conf.template)"
    echo "    or skip self-steal and use a third-party domain instead."
    echo "    See angie-selsteal.conf.template header for details."
else
    # Third-party mode (default).
    # Clear SELF_STEAL_DOMAIN if it was previously set (operator switched back).
    if [[ -n "${SELF_STEAL_DOMAIN:-}" ]]; then
        echo "  ℹ  TLS_DOMAIN is a known third-party domain. Clearing previous self-steal config."
        # Remove SELF_STEAL_DOMAIN from .env file.
        sed -i '/^SELF_STEAL_DOMAIN=/d' "$ENV_FILE" 2>/dev/null || true
        unset SELF_STEAL_DOMAIN || true
    fi

    # Set mask_host and mask_port for third-party mode (AC6).
    MASK_HOST="$TLS_DOMAIN"
    MASK_PORT=443
fi
export MASK_HOST
export MASK_PORT

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
            EXIT_KEYPAIR=$(docker run --rm ghcr.io/xtls/xray-core:latest x25519)
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
            EXIT_VLESS_UUID=$(docker run --rm ghcr.io/xtls/xray-core:latest uuid)
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
# N4 (TKT-024): default changed from www.microsoft.com to ads.x5.ru.
# www.microsoft.com (Akamai CDN) breaks the VLESS-Reality uTLS handshake —
# the ClientHello hangs with zero bytes sent (verified via xray tls ping).
# ads.x5.ru is the verified-working default. This is the Reality SNI for the
# entry->exit tunnel only; it is independent of the FakeTLS tls_domain.
if [[ -n "${EXIT_REALITY_SNI:-}" ]]; then
    echo "✓ EXIT_REALITY_SNI already set (from .env): $EXIT_REALITY_SNI"
else
    EXIT_REALITY_SNI="$(prompt_for "EXIT_REALITY_SNI" \
        "Enter exit Reality SNI (default: ads.x5.ru)" \
        "ads.x5.ru")"
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

# Substitute placeholders including mask_host and mask_port (AC5/AC6).
sed \
    -e "s|__AD_TAG__|${AD_TAG}|g" \
    -e "s|__TELEMT_SECRET__|${TELEMT_SECRET}|g" \
    -e "s|__TLS_DOMAIN__|${TLS_DOMAIN}|g" \
    -e "s|__AUTH_HEADER__|${AUTH_HEADER}|g" \
    -e "s|__MANAGEMENT_IPS__|${MANAGEMENT_IPS_TOML}|g" \
    -e "s|__MASK_HOST__|${MASK_HOST}|g" \
    -e "s|__MASK_PORT__|${MASK_PORT}|g" \
    "$CONFIG_TEMPLATE" > "$CONFIG_FILE"

echo "✓ Generated $CONFIG_FILE"
echo "  mask_host: $MASK_HOST"
echo "  mask_port: $MASK_PORT"

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

if [[ -n "${SELF_STEAL_DOMAIN:-}" ]]; then
    # Self-steal mode: use the self-steal template with TLS server block (AC4).
    if [[ ! -f "$ANGIE_SELSTEAL_TEMPLATE" ]]; then
        echo "ERROR: angie-selsteal.conf.template not found at $ANGIE_SELSTEAL_TEMPLATE" >&2
        exit 1
    fi
    sed \
        -e "s|__TLS_DOMAIN__|${SELF_STEAL_DOMAIN}|g" \
        -e "s|__TLS_CERT_PATH__|${TLS_CERT_PATH}|g" \
        -e "s|__TLS_KEY_PATH__|${TLS_KEY_PATH}|g" \
        "$ANGIE_SELSTEAL_TEMPLATE" > "$ANGIE_CONF"
    echo "✓ Generated $ANGIE_CONF (self-steal mode — TLS on :443 for $SELF_STEAL_DOMAIN)"
else
    # Third-party mode: use the default mask-host-only template.
    cp "$ANGIE_TEMPLATE" "$ANGIE_CONF"
    echo "✓ Generated $ANGIE_CONF (third-party mode — mask host on :8080 only)"
fi

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
    # In self-steal mode, :443 is also used by Angie for TLS cert serving.
    sudo ufw allow 443/tcp 2>/dev/null || true

    # Allow :8080/tcp for Angie mask host.
    sudo ufw allow 8080/tcp 2>/dev/null || true

    # Allow :80/tcp for certbot HTTP-01 challenge (self-steal mode only).
    if [[ -n "${SELF_STEAL_DOMAIN:-}" ]]; then
        sudo ufw allow 80/tcp 2>/dev/null || true
    fi

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
if [[ -n "${SELF_STEAL_DOMAIN:-}" ]]; then
    echo "  Mode:            self-steal (operator-owned domain)"
    echo "  Mask host:       https://$SELF_STEAL_DOMAIN (TLS on :443)"
    echo "  Mask port:       443"
    echo "  TLS cert:        $TLS_CERT_PATH"
else
    echo "  Mode:            third-party (default)"
    echo "  Mask host:       $TLS_DOMAIN (tls_emulation fetches on :443)"
    echo "  Mask port:       443"
fi
echo "  ad_tag:          $AD_TAG"
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
if [[ -n "${SELF_STEAL_DOMAIN:-}" ]]; then
    echo ""
    echo "  ── Self-steal cert renewal ────────────────────────────────────"
    echo "  Cert renewal is NOT automated. Add a cron job:"
    echo "    0 3 * * * certbot renew && docker restart telemt-mask"
fi
echo ""
echo "  Re-run this script to update configuration (idempotent)."
echo ""
