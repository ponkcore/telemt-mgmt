#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy-monitoring.sh — deploy Prometheus + Grafana on the monitoring server.
#
# Installs Prometheus and Grafana via Docker Compose. Configures Prometheus to
# scrape the exit server's telemt metrics endpoint (:9090). Provisions Grafana
# dashboards (telemt proxy health + per-user) and datasource automatically.
#
# Prompts for:
#   TELEMT_METRICS_ENDPOINT — exit server metrics URL (e.g. 10.0.0.5:9090)
#   GRAFANA_ADMIN_PASSWORD  — Grafana admin password (auto-generate option)
#
# Idempotent: on re-run, reads existing .env and skips prompts (INV-IDEMPOTENT).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Timing wrapper ──────────────────────────────────────────────────────────
_DEPLOY_START_TIME=$(date +%s)

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
PROMETHEUS_TEMPLATE="$SCRIPT_DIR/prometheus.yml.template"
PROMETHEUS_CONFIG="$SCRIPT_DIR/prometheus.yml"

# ── Pre-flight ──────────────────────────────────────────────────────────────
check_docker

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  telemt-mgmt — Monitoring Server Deploy (Prometheus + Grafana) ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Load existing config (idempotent re-run detection) ──────────────────────
# INV-IDEMPOTENT: load_env sources .env if it exists; prompt_for skips prompts
# when the variable is already set (AC1).
load_env "$ENV_FILE"

# ── Prompt for configuration ────────────────────────────────────────────────

# TELEMT_METRICS_ENDPOINT — exit server metrics endpoint (IP:9090)
TELEMT_METRICS_ENDPOINT="$(prompt_for "TELEMT_METRICS_ENDPOINT" \
    "Enter telemt metrics endpoint (exit server IP:9090, e.g. 10.0.0.5:9090)")"
save_env_var "$ENV_FILE" "TELEMT_METRICS_ENDPOINT" "$TELEMT_METRICS_ENDPOINT"

# GRAFANA_ADMIN_PASSWORD — admin password for Grafana (auto-generate option)
if [[ -n "${GRAFANA_ADMIN_PASSWORD:-}" ]]; then
    echo "✓ GRAFANA_ADMIN_PASSWORD already set (from .env)."
else
    printf "Generate Grafana admin password automatically? [Y/n]: "
    read -r gen_pass
    gen_pass="${gen_pass:-Y}"
    if [[ "${gen_pass,,}" == "y" || "${gen_pass,,}" == "yes" ]]; then
        GRAFANA_ADMIN_PASSWORD="$(generate_secret 16)"
        echo "✓ Generated GRAFANA_ADMIN_PASSWORD (32 hex chars)"
    else
        printf "Enter Grafana admin password: "
        read -r GRAFANA_ADMIN_PASSWORD
        if [[ -z "$GRAFANA_ADMIN_PASSWORD" ]]; then
            echo "ERROR: GRAFANA_ADMIN_PASSWORD is required." >&2
            exit 1
        fi
    fi
fi
export GRAFANA_ADMIN_PASSWORD
save_env_var "$ENV_FILE" "GRAFANA_ADMIN_PASSWORD" "$GRAFANA_ADMIN_PASSWORD"

echo ""
echo "✓ Configuration saved to $ENV_FILE"

# ── Generate prometheus.yml from template ───────────────────────────────────
echo "→ Generating prometheus.yml from template..."

sed "s|__TELEMT_METRICS_ENDPOINT__|${TELEMT_METRICS_ENDPOINT}|g" \
    "$PROMETHEUS_TEMPLATE" > "$PROMETHEUS_CONFIG"

echo "✓ Generated $PROMETHEUS_CONFIG"

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
echo "║  ✓ Monitoring server deployed successfully!                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Prometheus:  http://localhost:9090"
echo "  Grafana:     http://localhost:3000"
echo "  Metrics src: $TELEMT_METRICS_ENDPOINT"
echo ""
echo "  ── Next steps ────────────────────────────────────────────────"
echo "  Open Grafana at http://localhost:3000"
echo "  Login with admin / <your-password>"
echo "  Dashboards are auto-provisioned:"
echo "    - Telemt Proxy Health"
echo "    - Telemt Per-User Analytics"
echo ""
echo "  Re-run this script to update configuration (idempotent)."
echo ""
