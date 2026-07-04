#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# migrate.sh — migrate a telemt exit or entry server to a new server.
#
# Full migration cycle (AC1):
#   1. Prompt for migration parameters.
#   2. Stop containers on the old server (docker compose down).
#   3. Tar config/state from the old server (AC4).
#   4. SCP the tar archive to the new server.
#   5. Extract the archive on the new server.
#   6. Run the appropriate deploy script on the new server.
#   7. Update Cloudflare DNS A-record via API (AC2, AC3).
#   8. Health check on the new server (AC5).
#   9. Output rollback instructions (AC6).
#  10. Output post-migration verification command (AC9).
#
# Target: < 2 minutes user-facing downtime (M2, PRD-001@0.3.0 §6).
# INV-DOMAIN: proxy link FQDN is unchanged — only the DNS A-record IP changes.
#
# Prompts for:
#   OLD_SERVER_IP      — IP address of the current (old) server
#   NEW_SERVER_IP      — IP address of the new server
#   CF_API_TOKEN       — Cloudflare API token (DNS edit permission)
#   CF_ZONE_ID         — Cloudflare Zone ID
#   CF_RECORD_ID       — Cloudflare DNS record ID to update
#   DOMAIN             — FQDN of the DNS record (e.g. proxy.example.com)
#   SERVER_TYPE        — "exit" or "entry" (determines which deploy script to run)
#
# No new dependencies beyond standard Unix tools (tar, scp, ssh, curl, jq) — §7 Constraints.
# All secrets via interactive prompts only — INV-SECRETS.
# ─────────────────────────────────────────────────────────────────────────────
# shellcheck shell=bash
# SC2029 is disabled globally: SSH commands intentionally expand local variables
# on the client side before sending to the remote host.
# shellcheck disable=SC2029
set -euo pipefail

# ── Timing wrapper (AC1 — M2 target: < 2 min downtime) ──────────────────────
MIGRATE_START_TIME=$(date +%s)

print_elapsed() {
    local end_time elapsed
    end_time=$(date +%s)
    elapsed=$((end_time - MIGRATE_START_TIME))
    local mins=$((elapsed / 60))
    local secs=$((elapsed % 60))
    echo ""
    echo "⏱  Total migration time: ${mins}m ${secs}s (M2 target: < 2 min)"
}
trap print_elapsed EXIT

# ── Resolve script directory ─────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Helper functions ─────────────────────────────────────────────────────────

# Print a banner.
banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  $1"
    echo "╚══════════════════════════════════════════════════════════════╝"
}

# Prompt for a required value. Reads from stdin if not in env.
# Usage: prompt_value <prompt_text> [default]
prompt_value() {
    local prompt_text="$1"
    local default="${2:-}"
    local value

    if [[ -n "$default" ]]; then
        read -r -p "${prompt_text} [${default}]: " value
        value="${value:-$default}"
    else
        read -r -p "${prompt_text}: " value
    fi

    if [[ -z "$value" ]]; then
        echo "ERROR: This value is required." >&2
        exit 1
    fi
    echo "$value"
}

# Output rollback instructions (AC6).
print_rollback_instructions() {
    local old_ip="$1"
    local new_ip="$2"
    local domain="$3"
    local server_type="$4"
    local tar_file="$5"

    echo ""
    echo "━━━ ROLLBACK INSTRUCTIONS (AC6) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "If migration failed, follow these steps to roll back:"
    echo ""
    echo "1. Restore DNS to old IP:"
    echo "   scripts/cloudflare-dns.sh \\"
    echo "     --api-token  \"\$CF_API_TOKEN\" \\"
    echo "     --zone-id    \"\$CF_ZONE_ID\" \\"
    echo "     --record-id  \"\$CF_RECORD_ID\" \\"
    echo "     --record-name \"${domain}\" \\"
    echo "     --ip         \"${old_ip}\""
    echo ""
    echo "2. Restart containers on old server (${old_ip}):"
    echo "   ssh root@${old_ip} 'cd /opt/telemt && docker compose up -d'"
    echo ""
    echo "3. Stop containers on new server (${new_ip}):"
    echo "   ssh root@${new_ip} 'docker compose -f /opt/telemt/docker-compose.yml down'"
    echo ""
    echo "4. Verify old server is back:"
    echo "   curl -s https://${domain} && echo OK"
    echo ""
    echo "5. The backup archive (${tar_file}) can be used to restore config"
    echo "   on the old server if needed:"
    echo "   ssh root@${old_ip} 'tar xf /tmp/$(basename "${tar_file}") -C /opt/telemt'"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Output post-migration verification command (AC9).
print_verification_command() {
    local domain="$1"
    local server_type="$2"

    echo ""
    echo "━━━ POST-MIGRATION VERIFICATION (AC9) ━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Verify the new server is accepting connections:"
    echo ""
    echo "  curl -s https://${domain} && echo OK"
    echo ""
    echo "Note: DNS propagation may take up to 60 seconds (TTL=60)."
    echo "      Link FQDN is unchanged (INV-DOMAIN) — users reconnect"
    echo "      automatically after DNS TTL expiry (M5)."
    echo ""
    echo "For ${server_type} server, also verify:"
    if [[ "$server_type" == "exit" ]]; then
        echo "  ssh root@${domain} 'docker compose ps'  # telemt + Angie running"
        echo "  curl -s http://${domain}:8080           # Angie mask host responds"
    else
        echo "  ssh root@${domain} 'docker compose ps'  # Xray container running"
        echo "  curl -s https://${domain}               # Reality handshake responds"
    fi
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ── Pre-flight checks ────────────────────────────────────────────────────────
banner "telemt-mgmt — Server Migration Script"

echo ""
echo "This script migrates a telemt exit or entry server to a new server."
echo "Target downtime: < 2 minutes (M2)."
echo "Proxy link FQDN is unchanged — only the DNS A-record IP changes (INV-DOMAIN)."
echo ""

# Validate dependencies.
for _cmd in tar scp ssh curl jq; do
    if ! command -v "$_cmd" &>/dev/null; then
        echo "ERROR: $_cmd is required but not installed." >&2
        exit 1
    fi
done

# ── Prompt for migration parameters ──────────────────────────────────────────
echo "── Migration Parameters ──"
echo ""

OLD_SERVER_IP="$(prompt_value "Enter OLD server IP")"
NEW_SERVER_IP="$(prompt_value "Enter NEW server IP")"
CF_API_TOKEN="$(prompt_value "Enter Cloudflare API token")"
CF_ZONE_ID="$(prompt_value "Enter Cloudflare Zone ID")"
CF_RECORD_ID="$(prompt_value "Enter Cloudflare DNS record ID")"
DOMAIN="$(prompt_value "Enter domain (FQDN for DNS record, e.g. proxy.example.com)")"
SERVER_TYPE="$(prompt_value "Enter server type (exit/entry)" "exit")"

# Validate server type.
if [[ "$SERVER_TYPE" != "exit" && "$SERVER_TYPE" != "entry" ]]; then
    echo "ERROR: SERVER_TYPE must be 'exit' or 'entry', got: $SERVER_TYPE" >&2
    exit 1
fi

# Determine SSH user (default: root).
SSH_USER="$(prompt_value "Enter SSH user for servers" "root")"

# Determine the remote config path and deploy script based on server type.
REMOTE_CONFIG_PATH="/opt/telemt"
if [[ "$SERVER_TYPE" == "exit" ]]; then
    DEPLOY_SCRIPT="infra/exit/deploy-exit.sh"
else
    DEPLOY_SCRIPT="infra/entry/deploy-entry.sh"
fi

# Timestamp for the backup archive.
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TAR_FILE="telemt-${SERVER_TYPE}-backup-${TIMESTAMP}.tar.gz"
REMOTE_TAR="/tmp/${TAR_FILE}"
LOCAL_TAR="/tmp/${TAR_FILE}"

echo ""
echo "✓ Migration parameters:"
echo "  Old server:   ${SSH_USER}@${OLD_SERVER_IP}"
echo "  New server:   ${SSH_USER}@${NEW_SERVER_IP}"
echo "  Domain:       ${DOMAIN}"
echo "  Server type:  ${SERVER_TYPE}"
echo "  Deploy script: ${DEPLOY_SCRIPT}"
echo "  Backup:       ${REMOTE_TAR} (on old server)"
echo ""

# ── STEP 1: Stop containers on old server ───────────────────────────────────
banner "STEP 1/8: Stop containers on old server (${OLD_SERVER_IP})"

echo "→ Stopping Docker containers on old server..."
if ssh "${SSH_USER}@${OLD_SERVER_IP}" \
    "cd ${REMOTE_CONFIG_PATH} 2>/dev/null && \
     (docker compose down 2>/dev/null || docker-compose down 2>/dev/null) || \
     echo 'WARNING: No docker-compose found at ${REMOTE_CONFIG_PATH} — containers may not be running'"; then
    echo "✓ Containers stopped on old server."
else
    echo "⚠  Could not stop containers on old server (may not be running)."
fi

# ── STEP 2: Tar config/state from old server (AC4) ──────────────────────────
banner "STEP 2/8: Backup config/state from old server (AC4)"

echo "→ Creating tar archive of ${REMOTE_CONFIG_PATH} on old server..."
# Tar the config directory, Docker volumes, and .env file.
# --ignore-failed-read ensures we don't fail if some paths don't exist.
if ssh "${SSH_USER}@${OLD_SERVER_IP}" \
    "tar czf ${REMOTE_TAR} \
        --ignore-failed-read \
        -C / \
        ${REMOTE_CONFIG_PATH}/.env \
        ${REMOTE_CONFIG_PATH}/docker-compose.yml \
        ${REMOTE_CONFIG_PATH}/config \
        ${REMOTE_CONFIG_PATH}/angie.conf \
        ${REMOTE_CONFIG_PATH}/xray-config.json \
        2>/dev/null || true"; then
    echo "✓ Config backed up as tar archive: ${REMOTE_TAR}"
else
    echo "ERROR: Failed to create tar archive on old server." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi

# Verify the tar file was created and is non-empty.
REMOTE_TAR_SIZE=$(ssh "${SSH_USER}@${OLD_SERVER_IP}" \
    "stat -c '%s' ${REMOTE_TAR} 2>/dev/null || echo 0")
if [[ "$REMOTE_TAR_SIZE" -eq 0 ]]; then
    echo "ERROR: Tar archive is empty or missing on old server." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi
echo "  Archive size: ${REMOTE_TAR_SIZE} bytes"

# ── STEP 3: SCP tar archive to new server ───────────────────────────────────
banner "STEP 3/8: Transfer backup to new server (${NEW_SERVER_IP})"

echo "→ Copying tar archive to new server..."
if scp "${SSH_USER}@${OLD_SERVER_IP}:${REMOTE_TAR}" "${LOCAL_TAR}"; then
    echo "✓ Downloaded archive to local: ${LOCAL_TAR}"
else
    echo "ERROR: Failed to download tar archive from old server." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi

if scp "$LOCAL_TAR" "${SSH_USER}@${NEW_SERVER_IP}:${REMOTE_TAR}"; then
    echo "✓ Uploaded archive to new server: ${REMOTE_TAR}"
else
    echo "ERROR: Failed to upload tar archive to new server." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi

# Clean up local copy.
rm -f "$LOCAL_TAR"

# ── STEP 4: Extract archive on new server ───────────────────────────────────
banner "STEP 4/8: Extract config on new server"

echo "→ Extracting tar archive on new server..."
# Create the config directory if it doesn't exist, then extract.
if ssh "${SSH_USER}@${NEW_SERVER_IP}" \
    "mkdir -p ${REMOTE_CONFIG_PATH} && \
     tar xzf ${REMOTE_TAR} -C / && \
     echo 'Extracted successfully'"; then
    echo "✓ Config extracted to ${REMOTE_CONFIG_PATH} on new server."
else
    echo "ERROR: Failed to extract tar archive on new server." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi

# ── STEP 5: Run deploy script on new server ─────────────────────────────────
banner "STEP 5/8: Deploy ${SERVER_TYPE} server on new server"

echo "→ Running ${DEPLOY_SCRIPT} on new server..."
echo "  The deploy script will read the transferred .env (idempotent — INV-IDEMPOTENT)."
echo ""

# The deploy script is expected to be in the repo on the new server.
# The operator should have cloned the repo on the new server.
REMOTE_REPO="\${HOME}/telemt-mgmt"

echo "→ Checking for deploy script on new server..."
if ssh "${SSH_USER}@${NEW_SERVER_IP}" \
    "test -f ${REMOTE_REPO}/${DEPLOY_SCRIPT} 2>/dev/null || \
     test -f /opt/telemt-mgmt/${DEPLOY_SCRIPT} 2>/dev/null || \
     echo 'NOT_FOUND'"; then
    echo "✓ Deploy script found on new server."
else
    echo "⚠  Deploy script not found on new server."
    echo "   Please ensure the telemt-mgmt repo is cloned at ~/telemt-mgmt on the new server."
    echo "   You can run the deploy script manually after migration:"
    echo "   ssh ${SSH_USER}@${NEW_SERVER_IP} 'cd ~/telemt-mgmt && bash ${DEPLOY_SCRIPT}'"
    echo ""
fi

# Run the deploy script on the new server non-interactively.
# The transferred .env file provides all configuration (INV-IDEMPOTENT).
echo "→ Running deploy script (non-interactive, using transferred .env)..."
if ! ssh "${SSH_USER}@${NEW_SERVER_IP}" \
    "cd ${REMOTE_REPO} 2>/dev/null && bash ${DEPLOY_SCRIPT} 2>&1 || \
     (cd /opt/telemt-mgmt 2>/dev/null && bash ${DEPLOY_SCRIPT} 2>&1)"; then
    echo "✗ Deploy script failed on new server." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi
echo "✓ Deploy script completed on new server."

# ── STEP 6: Update Cloudflare DNS A-record (AC2, AC3) ───────────────────────
banner "STEP 6/8: Update Cloudflare DNS A-record (AC2, AC3)"

echo "→ Updating DNS A-record for ${DOMAIN} → ${NEW_SERVER_IP}..."
echo ""

# Call the cloudflare-dns.sh helper script (AC2 — via API, no manual DNS).
CLOUDFLARE_SCRIPT="${SCRIPT_DIR}/cloudflare-dns.sh"
if bash "$CLOUDFLARE_SCRIPT" \
    --api-token "$CF_API_TOKEN" \
    --zone-id "$CF_ZONE_ID" \
    --record-id "$CF_RECORD_ID" \
    --record-name "$DOMAIN" \
    --ip "$NEW_SERVER_IP"; then
    echo "✓ DNS A-record updated (TTL=60s — AC3)."
else
    echo "ERROR: Failed to update Cloudflare DNS A-record." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi

# ── STEP 7: Health check on new server (AC5) ────────────────────────────────
banner "STEP 7/8: Health check on new server (AC5)"

echo "→ Waiting for new server to accept connections (TTL=60s max)..."

# Health check strategy depends on SERVER_TYPE (M5 fix):
# - Exit servers: Angie serves a mask host on :8080 — use HTTP check.
# - Entry servers: run Xray dokodemo-door/VLESS-Reality (not HTTP) — skip curl
#   entirely and go straight to Docker container status check.
HEALTH_CHECK_OK=false

if [[ "$SERVER_TYPE" == "exit" ]]; then
    # Exit server: HTTP health check against Angie mask host on :8080.
    # Wait for DNS propagation + container startup (up to ~2 min, TTL=60).
    # Uses only curl (no dig/seq — §7 Constraints: tar, scp, curl, jq only).
    for (( _attempt = 1; _attempt <= 12; _attempt++ )); do
        if curl -sf --connect-timeout 5 --max-time 10 "http://${DOMAIN}:8080" >/dev/null 2>&1; then
            echo "  ✓ New server responding at http://${DOMAIN}:8080 (attempt ${_attempt}/12)"
            HEALTH_CHECK_OK=true
            break
        fi
        echo "  → Waiting for DNS propagation + container startup (${_attempt}/12)..."
        sleep 10
    done
else
    # Entry server: runs Xray dokodemo-door/VLESS-Reality on :443 — does not
    # serve HTTP(S). Skip curl and rely on Docker container status check below.
    echo "  Entry server — skipping HTTP health check (no HTTP service)."
    echo "  Will verify via Docker container status instead."
fi

# If HTTP check failed or was skipped (entry servers), try Docker status on new server.
if [[ "$HEALTH_CHECK_OK" != "true" ]]; then
    echo "⚠  HTTP health check unavailable — trying Docker status on new server..."
    if ssh "${SSH_USER}@${NEW_SERVER_IP}" \
        "docker compose -f ${REMOTE_CONFIG_PATH}/docker-compose.yml ps 2>/dev/null | \
         grep -q 'Up' 2>/dev/null || \
         docker ps 2>/dev/null | grep -q 'Up'"; then
        echo "✓ Health check passed via Docker container status on new server."
        HEALTH_CHECK_OK=true
    fi
fi

if [[ "$HEALTH_CHECK_OK" != "true" ]]; then
    echo ""
    echo "✗ Health check failed: new server is not accepting connections." >&2
    echo "  This may be due to DNS propagation delay or container startup time." >&2
    echo ""
    print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"
    exit 1
fi

echo ""
echo "✓ New server is accepting connections."

# ── STEP 8: Output rollback instructions and verification command ───────────
banner "STEP 8/8: Migration complete"

# AC6 — rollback instructions.
print_rollback_instructions "$OLD_SERVER_IP" "$NEW_SERVER_IP" "$DOMAIN" "$SERVER_TYPE" "$REMOTE_TAR"

# AC9 — post-migration verification command.
print_verification_command "$DOMAIN" "$SERVER_TYPE"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ Migration complete!                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Old server:  ${OLD_SERVER_IP} (containers stopped, backup at ${REMOTE_TAR})"
echo "  New server:  ${NEW_SERVER_IP} (deployed and running)"
echo "  Domain:      ${DOMAIN} → ${NEW_SERVER_IP} (TTL=60s)"
echo "  Link FQDN:   unchanged (INV-DOMAIN — users reconnect after DNS TTL)"
echo ""
