"""Unit tests for telemt_proxy.link — proxy link builder.

Tests cover (AC3, AC7):
  - build_proxy_link returns the correct tg://proxy?server=...&port=...&secret=... format.
  - The server= field contains the domain name (INV-DOMAIN).
  - Different inputs produce different links.
  - Port is rendered as a string in the URL.
"""

from __future__ import annotations

import re

from telemt_proxy.link import build_proxy_link


class TestBuildProxyLink:
    """Tests for build_proxy_link (AC3, AC7)."""

    def test_ac3_exact_format(self) -> None:
        """AC3: build_proxy_link('proxy.example.com', 443, 'ee...') returns exact format."""
        result = build_proxy_link("proxy.example.com", 443, "ee")
        assert result == "tg://proxy?server=proxy.example.com&port=443&secret=ee"

    def test_returns_tg_proxy_scheme(self) -> None:
        """Result starts with tg://proxy?."""
        result = build_proxy_link("proxy.example.com", 443, "secret123")
        assert result.startswith("tg://proxy?")

    def test_contains_server_field(self) -> None:
        """Result contains server=<domain>."""
        result = build_proxy_link("proxy.example.com", 443, "secret123")
        assert "server=proxy.example.com" in result

    def test_contains_port_field(self) -> None:
        """Result contains port=<port>."""
        result = build_proxy_link("proxy.example.com", 443, "secret123")
        assert "port=443" in result

    def test_contains_secret_field(self) -> None:
        """Result contains secret=<secret>."""
        result = build_proxy_link("proxy.example.com", 443, "mysecret")
        assert "secret=mysecret" in result

    def test_ac7_domain_in_server_field(self) -> None:
        """AC7: server= field uses a domain name, not a raw IP (INV-DOMAIN)."""
        domain = "proxy.telemt.example.com"
        result = build_proxy_link(domain, 443, "secret")
        # Extract the server= value
        match = re.search(r"server=([^&]+)", result)
        assert match is not None
        server_value = match.group(1)
        # Domain names contain dots and letters, not just numbers
        # (a raw IP would be all digits and dots)
        assert "." in server_value
        assert not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", server_value)

    def test_different_servers_produce_different_links(self) -> None:
        """Different server domains produce different links."""
        link1 = build_proxy_link("server1.example.com", 443, "secret")
        link2 = build_proxy_link("server2.example.com", 443, "secret")
        assert link1 != link2

    def test_different_ports_produce_different_links(self) -> None:
        """Different ports produce different links."""
        link1 = build_proxy_link("proxy.example.com", 443, "secret")
        link2 = build_proxy_link("proxy.example.com", 8080, "secret")
        assert link1 != link2

    def test_different_secrets_produce_different_links(self) -> None:
        """Different secrets produce different links."""
        link1 = build_proxy_link("proxy.example.com", 443, "secret1")
        link2 = build_proxy_link("proxy.example.com", 443, "secret2")
        assert link1 != link2

    def test_full_url_format_regex(self) -> None:
        """Full URL matches the expected regex pattern."""
        result = build_proxy_link("proxy.example.com", 443, "ee")
        pattern = r"^tg://proxy\?server=[^&]+&port=\d+&secret=.+$"
        assert re.fullmatch(pattern, result) is not None

    def test_empty_secret(self) -> None:
        """Empty secret produces a link with empty secret= (edge case)."""
        result = build_proxy_link("proxy.example.com", 443, "")
        assert "secret=" in result
        assert result == "tg://proxy?server=proxy.example.com&port=443&secret="

    def test_large_port(self) -> None:
        """Large port numbers are rendered correctly."""
        result = build_proxy_link("proxy.example.com", 65535, "secret")
        assert "port=65535" in result
