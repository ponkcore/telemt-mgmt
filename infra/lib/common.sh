#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# common.sh — shared deploy helper functions for telemt-mgmt deploy scripts.
#
# Used by: infra/entry/deploy-entry.sh, infra/exit/deploy-exit.sh,
#          infra/mgmt/deploy-mgmt.sh, infra/monitoring/deploy-monitoring.sh,
#          infra/landing/deploy-landing.sh, scripts/migrate.sh
#
# Sourcing:  source "$(dirname "$0")/lib/common.sh"
#
# All functions respect INV-IDEMPOTENT (project.jsonc invariants):
# prompts are skipped if the value already exists in the .env file (re-run detection).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# check_docker — verifies Docker and docker compose are installed.
# Exits with code 1 and prints a helpful message if not found.
check_docker() {
    if ! command -v docker &>/dev/null; then
        echo "ERROR: Docker is not installed. Install it first: https://docs.docker.com/get-docker/" >&2
        exit 1
    fi
    if ! docker compose version &>/dev/null 2>&1 && ! docker-compose version &>/dev/null 2>&1; then
        echo "ERROR: Docker Compose is not installed. Install it: https://docs.docker.com/compose/install/" >&2
        exit 1
    fi
    echo "✓ Docker and Docker Compose are available."
}

# load_env — sources an .env file if it exists.
# Usage: load_env /path/to/.env
load_env() {
    local env_file="$1"
    if [[ -f "$env_file" ]]; then
        # shellcheck disable=SC1090
        source "$env_file"
    fi
}

# prompt_for — reads a value from .env if present, otherwise prompts interactively.
# Supports re-run detection: if the variable is already set in the env file, the
# prompt is skipped (INV-IDEMPOTENT).
#
# Usage: prompt_for <var_name> <prompt_text> [default_value]
#
# Outputs the value to stdout and exports it as <var_name> in the calling shell.
# If the variable already exists in the environment (from load_env), it is used
# without prompting.
prompt_for() {
    local var_name="$1"
    local prompt_text="$2"
    local default_value="${3:-}"

    # Re-run detection: if the variable is already set in environment, use it.
    local current_value="${!var_name:-}"
    if [[ -n "$current_value" ]]; then
        echo "$current_value"
        return 0
    fi

    # Build prompt string
    local prompt="${prompt_text}"
    if [[ -n "$default_value" ]]; then
        prompt="${prompt_text} [${default_value}]"
    fi
    prompt="${prompt}: "

    # Read interactively (secrets are visible — deploy scripts run as root interactively)
    local value
    read -r -p "$prompt" value
    value="${value:-$default_value}"

    if [[ -z "$value" ]]; then
        echo "ERROR: ${var_name} is required and cannot be empty." >&2
        exit 1
    fi

    # Export into the calling shell
    printf -v "$var_name" '%s' "$value"
    export "$var_name"
    echo "$value"
}

# save_env_var — appends or updates a key=value pair in an .env file.
# Usage: save_env_var <env_file> <key> <value>
save_env_var() {
    local env_file="$1"
    local key="$2"
    local value="$3"

    # Create the file if it doesn't exist
    touch "$env_file"

    # If the key already exists, replace its line; otherwise append.
    if grep -q "^${key}=" "$env_file" 2>/dev/null; then
        # Use a delimiter unlikely to appear in values
        local escaped_value
        escaped_value=$(printf '%s\n' "$value" | sed 's/[&/\]/\\&/g')
        sed -i "s|^${key}=.*|${key}=${escaped_value}|" "$env_file"
    else
        printf '%s=%s\n' "$key" "$value" >> "$env_file"
    fi
}

# generate_secret — generates a random hex string of the given length (bytes).
# Usage: generate_secret [length]  (default: 32 bytes → 64 hex chars)
generate_secret() {
    local length="${1:-32}"
    head -c "$length" /dev/urandom | xxd -p | tr -d '\n'
}

# sanitize_input — strips dangerous characters from user-provided input to
# prevent injection into sed substitutions and config file generation.
#
# Removes: single quotes ('), double quotes ("), backticks (`), semicolons (;).
# These characters can break sed with | delimiter, execute subshells (backticks),
# or chain commands (semicolons) if the value reaches a shell expansion.
#
# Does NOT strip: hyphens, dots, colons, slashes, underscores, alphanumeric —
# these are legitimate in domain names (example.com), IPs (10.0.0.5), CIDR
# notation (10.0.0.5/32), base64 keys (a-b_C), and hex values (deadbeef).
#
# Usage: sanitized_value="$(sanitize_input "$raw_value")"
#
# Per BACKLOG-004 / BACKLOG-007 (TKT-026).
sanitize_input() {
    local input="$1"
    # Strip single quotes, double quotes, backticks, semicolons.
    printf '%s' "$input" | tr -d "'\";\`"
}
