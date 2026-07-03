"""Unit tests for telemt_proxy.qr — QR code generation.

Tests cover (AC10):
  - generate_qr returns bytes (not None, not str).
  - The returned bytes are valid PNG data (PNG magic number).
  - Different links produce different QR images.
  - The QR code can be decoded back to the original link (round-trip).
  - Empty string does not crash.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from telemt_proxy.qr import generate_qr

# PNG magic number: \x89PNG\r\n\x1a\n
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# A sample proxy link for testing.
SAMPLE_LINK = "tg://proxy?server=proxy.example.com&port=443&secret=ee"


class TestGenerateQr:
    """Tests for generate_qr (AC10)."""

    def test_returns_bytes(self) -> None:
        """generate_qr returns bytes (not str, not None)."""
        result = generate_qr(SAMPLE_LINK)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_returns_valid_png(self) -> None:
        """The returned bytes start with the PNG magic number."""
        result = generate_qr(SAMPLE_LINK)
        assert result[:8] == PNG_MAGIC

    def test_png_can_be_opened_by_pil(self) -> None:
        """The returned bytes can be opened as a PIL Image."""
        result = generate_qr(SAMPLE_LINK)
        img = Image.open(io.BytesIO(result))
        assert img.format == "PNG"
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_png_is_square(self) -> None:
        """The QR code PNG is roughly square (width ≈ height)."""
        result = generate_qr(SAMPLE_LINK)
        img = Image.open(io.BytesIO(result))
        width, height = img.size
        assert width == height

    def test_different_links_produce_different_images(self) -> None:
        """Different links produce different QR PNG data."""
        qr1 = generate_qr("tg://proxy?server=a.example.com&port=443&secret=aa")
        qr2 = generate_qr("tg://proxy?server=b.example.com&port=443&secret=bb")
        assert qr1 != qr2

    def test_same_link_produces_same_image(self) -> None:
        """Same link produces identical QR PNG data (deterministic)."""
        qr1 = generate_qr(SAMPLE_LINK)
        qr2 = generate_qr(SAMPLE_LINK)
        assert qr1 == qr2

    def test_qr_decodes_back_to_link(self) -> None:
        """The QR code can be decoded back to the original link (round-trip).

        This requires the pyzbar library. If not installed, the test is
        skipped — the PNG validity tests above are sufficient for AC10.
        """
        pytest.importorskip("pyzbar")
        from pyzbar.pyzbar import decode

        result = generate_qr(SAMPLE_LINK)
        decoded = decode(Image.open(io.BytesIO(result)))
        assert len(decoded) > 0
        assert decoded[0].data.decode() == SAMPLE_LINK

    def test_empty_string_does_not_crash(self) -> None:
        """Empty string input produces a valid (empty) QR code."""
        result = generate_qr("")
        assert isinstance(result, bytes)
        assert result[:8] == PNG_MAGIC

    def test_long_link(self) -> None:
        """A long proxy link produces a valid PNG."""
        long_link = "tg://proxy?server=" + "a" * 200 + ".example.com&port=443&secret=" + "x" * 100
        result = generate_qr(long_link)
        assert result[:8] == PNG_MAGIC
