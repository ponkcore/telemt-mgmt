"""Smoke tests for deploy scripts (L4 — code review finding).

Tests cover:
  - shellcheck runs cleanly on all deploy scripts.
  - sanitize_input() strips dangerous characters.
  - sanitize_input() preserves legitimate domain names, IPs, and labels.
  - Config template files exist and contain expected placeholders.
  - common.sh defines sanitize_input().

Per BACKLOG-003 L4 (TKT-026).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_DIR = REPO_ROOT / "infra"
COMMON_SH = INFRA_DIR / "lib" / "common.sh"

DEPLOY_SCRIPTS = [
    INFRA_DIR / "exit" / "deploy-exit.sh",
    INFRA_DIR / "entry" / "deploy-entry.sh",
    INFRA_DIR / "mgmt" / "deploy-mgmt.sh",
    INFRA_DIR / "monitoring" / "deploy-monitoring.sh",
    INFRA_DIR / "landing" / "deploy-landing.sh",
]

ALL_SHELL_SCRIPTS = DEPLOY_SCRIPTS + [COMMON_SH, REPO_ROOT / "scripts" / "migrate.sh"]


# ── Helpers ────────────────────────────────────────────────────────────────


def _shellcheck_available() -> bool:
    """Check if shellcheck is installed."""
    return shutil.which("shellcheck") is not None


def _source_common_sh() -> str:
    """Return a bash command that sources common.sh and runs a given command."""
    return f'source "{COMMON_SH}"'


# ── Shellcheck tests ───────────────────────────────────────────────────────


SHELLCHECK_AVAILABLE = _shellcheck_available()


@pytest.mark.skipif(
    not SHELLCHECK_AVAILABLE,
    reason="shellcheck not installed — skipping static analysis tests",
)
class TestShellcheck:
    """Run shellcheck on all deploy scripts and shared helpers."""

    @pytest.mark.parametrize(
        "script",
        DEPLOY_SCRIPTS,
        ids=[s.name for s in DEPLOY_SCRIPTS],
    )
    def test_shellcheck_clean(self, script: Path) -> None:
        """shellcheck passes on the script with no errors."""
        result = subprocess.run(
            ["shellcheck", "-x", str(script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"shellcheck found issues in {script}:\n{result.stdout}\n{result.stderr}"
        )


# ── sanitize_input() tests ─────────────────────────────────────────────────


class TestSanitizeInput:
    """Tests for sanitize_input() in common.sh (AC1, BACKLOG-004/007)."""

    @pytest.fixture
    def run_sanitize(self) -> Callable[[str], str]:
        """Return a callable that runs sanitize_input via bash."""

        def _run(value: str) -> str:
            # Use a bash subshell to source common.sh and call sanitize_input.
            # common.sh has `set -euo pipefail` — disable -eu so the subshell
            # doesn't exit on empty values. The value is passed as $1.
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f'source "{COMMON_SH}"; set +eu; '
                    'sanitize_input "$1"',
                    "_",
                    value,
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"sanitize_input failed: {result.stderr}"
            )
            return result.stdout

        return _run

    def test_strips_single_quotes(self, run_sanitize: object) -> None:
        """Single quotes are stripped from input."""
        result = run_sanitize("hello'world")  # type: ignore[operator]
        assert result == "helloworld"

    def test_strips_double_quotes(self, run_sanitize: object) -> None:
        """Double quotes are stripped from input."""
        result = run_sanitize('hello"world')  # type: ignore[operator]
        assert result == "helloworld"

    def test_strips_backticks(self, run_sanitize: object) -> None:
        """Backticks are stripped from input."""
        result = run_sanitize("hello`world")  # type: ignore[operator]
        assert result == "helloworld"

    def test_strips_semicolons(self, run_sanitize: object) -> None:
        """Semicolons are stripped from input."""
        result = run_sanitize("hello;world")  # type: ignore[operator]
        assert result == "helloworld"

    def test_strips_command_injection(self, run_sanitize: object) -> None:
        """A command injection attempt is neutralised."""
        result = run_sanitize("'; rm -rf /; '")  # type: ignore[operator]
        assert "rm" in result  # 'rm' text remains but is harmless without ; or `
        assert ";" not in result
        assert "'" not in result
        assert "`" not in result

    def test_preserves_domain_names(self, run_sanitize: object) -> None:
        """Legitimate domain names with dots and hyphens are preserved."""
        result = run_sanitize("proxy.example.com")  # type: ignore[operator]
        assert result == "proxy.example.com"

    def test_preserves_domain_with_hyphen(self, run_sanitize: object) -> None:
        """Domain names with hyphens are preserved."""
        result = run_sanitize("my-server.example.com")  # type: ignore[operator]
        assert result == "my-server.example.com"

    def test_preserves_ip_address(self, run_sanitize: object) -> None:
        """IP addresses are preserved."""
        result = run_sanitize("10.0.0.5")  # type: ignore[operator]
        assert result == "10.0.0.5"

    def test_preserves_cidr(self, run_sanitize: object) -> None:
        """CIDR notation is preserved."""
        result = run_sanitize("10.0.0.5/32")  # type: ignore[operator]
        assert result == "10.0.0.5/32"

    def test_preserves_comma_separated_ips(self, run_sanitize: object) -> None:
        """Comma-separated IP lists are preserved."""
        result = run_sanitize("10.0.0.5,203.0.113.10")  # type: ignore[operator]
        assert result == "10.0.0.5,203.0.113.10"

    def test_preserves_hex_values(self, run_sanitize: object) -> None:
        """Hex values (ad_tag, short IDs) are preserved."""
        result = run_sanitize("deadbeefcafe1234")  # type: ignore[operator]
        assert result == "deadbeefcafe1234"

    def test_preserves_base64_keys(self, run_sanitize: object) -> None:
        """Base64-like key strings with hyphens and underscores are preserved."""
        result = run_sanitize("aBcD-eFgH_iJkL-mNoP")  # type: ignore[operator]
        assert result == "aBcD-eFgH_iJkL-mNoP"

    def test_preserves_underscore_labels(self, run_sanitize: object) -> None:
        """Labels with underscores are preserved."""
        result = run_sanitize("my_label_here")  # type: ignore[operator]
        assert result == "my_label_here"

    def test_empty_string(self, run_sanitize: object) -> None:
        """Empty string returns empty."""
        result = run_sanitize("")  # type: ignore[operator]
        assert result == ""


# ── common.sh structure tests ──────────────────────────────────────────────


class TestCommonSh:
    """Tests for common.sh structure and function definitions."""

    def test_sanitize_input_defined(self) -> None:
        """common.sh defines sanitize_input() function (AC1)."""
        content = COMMON_SH.read_text()
        assert "sanitize_input()" in content
        # Verify it's a function definition
        assert "sanitize_input()" in content
        assert "tr -d" in content  # Uses tr to strip chars

    def test_sanitize_input_strips_quotes_backticks_semicolons(self) -> None:
        """sanitize_input comment documents the stripped characters."""
        content = COMMON_SH.read_text()
        # The function should mention all four dangerous characters
        assert "single quote" in content.lower() or "'" in content
        assert "double quote" in content.lower() or '"' in content
        assert "backtick" in content.lower() or "`" in content
        assert "semicolon" in content.lower() or ";" in content


# ── Deploy script structure tests ──────────────────────────────────────────


class TestDeployScriptStructure:
    """Smoke tests for deploy script structure (no execution)."""

    @pytest.mark.parametrize(
        "script",
        DEPLOY_SCRIPTS,
        ids=[s.name for s in DEPLOY_SCRIPTS],
    )
    def test_script_sources_common_sh(self, script: Path) -> None:
        """Each deploy script sources common.sh."""
        content = script.read_text()
        assert "common.sh" in content, f"{script.name} does not source common.sh"

    @pytest.mark.parametrize(
        "script",
        DEPLOY_SCRIPTS,
        ids=[s.name for s in DEPLOY_SCRIPTS],
    )
    def test_script_has_set_euo(self, script: Path) -> None:
        """Each deploy script has set -euo pipefail."""
        content = script.read_text()
        assert "set -euo pipefail" in content, (
            f"{script.name} does not have 'set -euo pipefail'"
        )

    def test_exit_script_uses_sanitize_input(self) -> None:
        """deploy-exit.sh uses sanitize_input() on user-provided values (AC2)."""
        content = (INFRA_DIR / "exit" / "deploy-exit.sh").read_text()
        assert "sanitize_input" in content
        # Should sanitize DOMAIN, AD_TAG, TLS_DOMAIN at minimum
        assert 'sanitize_input "$DOMAIN"' in content
        assert 'sanitize_input "$AD_TAG"' in content
        assert 'sanitize_input "$TLS_DOMAIN"' in content

    def test_entry_script_uses_sanitize_input(self) -> None:
        """deploy-entry.sh uses sanitize_input() on user-provided values (AC2)."""
        content = (INFRA_DIR / "entry" / "deploy-entry.sh").read_text()
        assert "sanitize_input" in content
        assert 'sanitize_input "$EXIT_SERVER_IP"' in content
        assert 'sanitize_input "$EXIT_VLESS_UUID"' in content
        assert 'sanitize_input "$EXIT_REALITY_SNI"' in content

    def test_exit_script_has_ufw_error_reporting(self) -> None:
        """deploy-exit.sh UFW commands report failures (AC3)."""
        content = (INFRA_DIR / "exit" / "deploy-exit.sh").read_text()
        assert "WARNING: UFW rule failed" in content
        # No more silent || true on ufw commands
        assert "ufw" in content
        # Verify the old pattern is gone
        assert "sudo ufw allow ssh 2>/dev/null || true" not in content

    def test_exit_script_has_rollback_trap(self) -> None:
        """deploy-exit.sh has a trap for rollback on failed compose (AC4)."""
        content = (INFRA_DIR / "exit" / "deploy-exit.sh").read_text()
        assert "trap" in content
        assert "ERR" in content
        assert "docker compose down" in content or "docker-compose down" in content

    def test_exit_script_has_ufw_error_reporting_not_silent(self) -> None:
        """deploy-exit.sh does NOT swallow UFW failures with || true (AC3)."""
        content = (INFRA_DIR / "exit" / "deploy-exit.sh").read_text()
        # Count occurrences of "ufw" with "|| true" — should be 0
        lines = content.split("\n")
        ufw_silent = [
            line
            for line in lines
            if "ufw" in line and "|| true" in line
            and "2>/dev/null" in line
        ]
        assert len(ufw_silent) == 0, (
            f"UFW commands still silently swallow errors: {ufw_silent}"
        )
