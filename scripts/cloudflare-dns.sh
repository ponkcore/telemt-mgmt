#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# cloudflare-dns.sh — update a Cloudflare DNS A-record to point to a new server IP.
#
# Used by: scripts/migrate.sh (AC2 — Cloudflare DNS A-record updated via API).
#
# Usage:
#   scripts/cloudflare-dns.sh \
#       --api-token   <CF_API_TOKEN> \
#       --zone-id     <CF_ZONE_ID> \
#       --record-id   <CF_RECORD_ID> \
#       --record-name <FQDN> \
#       --ip          <NEW_IP>
#
# Optional:
#   --ttl  <seconds>        (default: 60 — AC3, PRD-001@0.3.0 §7 requires TTL=60)
#   --proxied <true|false>  (default: false — DNS-only per PRD-001@0.3.0 §7)
#
# No new dependencies beyond standard Unix tools (curl, jq) — §7 Constraints.
# All secrets via args only — INV-SECRETS.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Defaults (AC3: TTL=60 per PRD-001@0.3.0 §7) ──────────────────────────────
TTL="60"
PROXIED="false"
API_TOKEN=""
ZONE_ID=""
RECORD_ID=""
RECORD_NAME=""
NEW_IP=""

# ── Usage ────────────────────────────────────────────────────────────────────
usage() {
    cat << 'USAGE'
Usage: cloudflare-dns.sh [OPTIONS]

Required:
  --api-token   STR   Cloudflare API token (DNS edit permission)
  --zone-id     STR   Cloudflare Zone ID
  --record-id   STR   DNS record ID to update
  --record-name STR   DNS record name (FQDN, e.g. proxy.example.com)
  --ip          STR   New IP address for the A-record

Optional:
  --ttl         INT   TTL in seconds (default: 60, per PRD-001@0.3.0 §7)
  --proxied     BOOL  Cloudflare proxy (default: false — DNS-only/grey cloud)
  -h, --help          Show this help message
USAGE
    exit "${1:-0}"
}

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-token)
            API_TOKEN="${2:?--api-token requires a value}"
            shift 2
            ;;
        --zone-id)
            ZONE_ID="${2:?--zone-id requires a value}"
            shift 2
            ;;
        --record-id)
            RECORD_ID="${2:?--record-id requires a value}"
            shift 2
            ;;
        --record-name)
            RECORD_NAME="${2:?--record-name requires a value}"
            shift 2
            ;;
        --ip)
            NEW_IP="${2:?--ip requires a value}"
            shift 2
            ;;
        --ttl)
            TTL="${2:?--ttl requires a value}"
            shift 2
            ;;
        --proxied)
            PROXIED="${2:?--proxied requires a value}"
            shift 2
            ;;
        -h|--help)
            usage 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            usage 1
            ;;
    esac
done

# Convert VAR_NAME to --var-name for error messages.
_var_to_flag() {
    local var="$1"
    local lower="${var,,}"
    echo "--${lower//_/-}"
}

# ── Validate required arguments ──────────────────────────────────────────────
_required_vars=(API_TOKEN ZONE_ID RECORD_ID RECORD_NAME NEW_IP)
for _var in "${_required_vars[@]}"; do
    if [[ -z "${!_var:-}" ]]; then
        echo "ERROR: $(_var_to_flag "$_var") is required." >&2
        exit 1
    fi
done

# ── Validate dependencies ────────────────────────────────────────────────────
for _cmd in curl jq; do
    if ! command -v "$_cmd" &>/dev/null; then
        echo "ERROR: $_cmd is required but not installed." >&2
        exit 1
    fi
done

# ── Update Cloudflare DNS A-record (AC2) ─────────────────────────────────────
# Cloudflare API: PATCH /zones/{zone_id}/dns_records/{record_id}
# Sets type=A, name=FQDN, content=NEW_IP, ttl=TTL, proxied=false (DNS-only).
API_URL="https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records/${RECORD_ID}"

echo "→ Updating Cloudflare DNS A-record..."
echo "  Record:   ${RECORD_NAME}"
echo "  New IP:   ${NEW_IP}"
echo "  TTL:      ${TTL}s (AC3 — PRD-001@0.3.0 §7 requires 60s)"
echo "  Proxied:  ${PROXIED} (DNS-only/grey cloud)"

# Build JSON payload using jq for safe escaping (no string injection).
PAYLOAD=$(jq -n \
    --arg type "A" \
    --arg name "$RECORD_NAME" \
    --arg content "$NEW_IP" \
    --argjson ttl "$TTL" \
    --argjson proxied "$PROXIED" \
    '{type: $type, name: $name, content: $content, ttl: $ttl, proxied: $proxied}')

# Call Cloudflare API (AC2 — no manual DNS changes).
HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X PATCH "$API_URL" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

# Split response body and HTTP status code.
HTTP_BODY=$(echo "$HTTP_RESPONSE" | sed '$d')
HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tail -n1)

# Check HTTP status.
if [[ "$HTTP_STATUS" != "200" ]]; then
    echo "ERROR: Cloudflare API returned HTTP ${HTTP_STATUS}." >&2
    echo "$HTTP_BODY" | jq '.' 2>/dev/null || echo "$HTTP_BODY" >&2
    exit 1
fi

# Check Cloudflare success flag.
CF_SUCCESS=$(echo "$HTTP_BODY" | jq -r '.success // false')
if [[ "$CF_SUCCESS" != "true" ]]; then
    echo "ERROR: Cloudflare API returned success=false." >&2
    echo "$HTTP_BODY" | jq '.errors' 2>/dev/null || echo "$HTTP_BODY" >&2
    exit 1
fi

# Verify the updated record.
UPDATED_IP=$(echo "$HTTP_BODY" | jq -r '.result.content // empty')
UPDATED_TTL=$(echo "$HTTP_BODY" | jq -r '.result.ttl // empty')

echo ""
echo "✓ Cloudflare DNS A-record updated successfully."
echo "  Record:   ${RECORD_NAME}"
echo "  IP:       ${UPDATED_IP}"
echo "  TTL:      ${UPDATED_TTL}s"

# Verify TTL is 60 (AC3).
if [[ "$UPDATED_TTL" != "60" ]]; then
    echo "⚠  Warning: TTL is ${UPDATED_TTL}, expected 60 (AC3)." >&2
fi
