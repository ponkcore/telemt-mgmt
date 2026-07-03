"""Unit tests for telemt_proxy.hashing — Telegram ID hashing.

Tests cover (AC2):
  - hash_telegram_id returns a deterministic 16-char hex string.
  - Same input + salt always produces the same output (determinism).
  - Different Telegram IDs produce different hashes.
  - Different salts produce different hashes for the same ID.
  - hash_telegram_id_full returns a 64-char hex string.
  - The first 16 chars of the full hash match hash_telegram_id.
  - Salt validation: short salts raise ValueError.

Per ADR-005@0.1.0 and INV-HASH, this is the ONLY place where
sha256(telegram_id + salt) is computed.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from telemt_proxy.hashing import hash_telegram_id, hash_telegram_id_full

# ── Constants ──────────────────────────────────────────────────────────────

TEST_SALT = "test_salt_at_least_16_chars"
SHORT_SALT = "short"

# ── AC2: Deterministic 16-char hex ─────────────────────────────────────────


class TestHashTelegramId:
    """Tests for hash_telegram_id (AC2)."""

    def test_returns_16_char_string(self) -> None:
        """hash_telegram_id returns exactly 16 characters."""
        result = hash_telegram_id(12345, TEST_SALT)
        assert len(result) == 16

    def test_returns_hex_string(self) -> None:
        """hash_telegram_id returns only hex characters [0-9a-f]."""
        result = hash_telegram_id(12345, TEST_SALT)
        assert re.fullmatch(r"[0-9a-f]{16}", result) is not None

    def test_deterministic_same_input_same_output(self) -> None:
        """Same input + salt always produces the same output."""
        result1 = hash_telegram_id(12345, TEST_SALT)
        result2 = hash_telegram_id(12345, TEST_SALT)
        assert result1 == result2

    def test_ac2_specific_value(self) -> None:
        """AC2: hash_telegram_id(12345, 'test_salt') matches manual computation."""
        # Note: the AC says "test_salt" but our function requires >=16 chars.
        # We use the full 16+ char salt and verify the computation matches.
        expected = hashlib.sha256(
            (str(12345) + TEST_SALT).encode(),
        ).hexdigest()[:16]
        result = hash_telegram_id(12345, TEST_SALT)
        assert result == expected

    def test_different_ids_produce_different_hashes(self) -> None:
        """Different Telegram IDs produce different hashes."""
        hash1 = hash_telegram_id(12345, TEST_SALT)
        hash2 = hash_telegram_id(67890, TEST_SALT)
        assert hash1 != hash2

    def test_different_salts_produce_different_hashes(self) -> None:
        """Same ID with different salts produces different hashes."""
        salt_a = "salt_a_min_16_chars!"
        salt_b = "salt_b_min_16_chars!"
        hash_a = hash_telegram_id(12345, salt_a)
        hash_b = hash_telegram_id(12345, salt_b)
        assert hash_a != hash_b

    def test_large_telegram_id(self) -> None:
        """Large Telegram IDs (up to 2^31-1) hash correctly."""
        result = hash_telegram_id(999999999, TEST_SALT)
        assert len(result) == 16
        assert re.fullmatch(r"[0-9a-f]{16}", result) is not None

    def test_id_zero(self) -> None:
        """Telegram ID 0 hashes correctly (edge case)."""
        result = hash_telegram_id(0, TEST_SALT)
        assert len(result) == 16
        assert re.fullmatch(r"[0-9a-f]{16}", result) is not None

    def test_negative_id_raises(self) -> None:
        """Negative Telegram IDs should still hash (no validation on sign).

        Telegram IDs are always positive, but the function should not
        crash — it just converts to string.
        """
        result = hash_telegram_id(-1, TEST_SALT)
        assert len(result) == 16


# ── Salt validation ────────────────────────────────────────────────────────


class TestSaltValidation:
    """Tests for salt length validation."""

    def test_short_salt_raises_value_error(self) -> None:
        """Salt shorter than 16 characters raises ValueError."""
        with pytest.raises(ValueError, match="at least 16 characters"):
            hash_telegram_id(12345, SHORT_SALT)

    def test_short_salt_raises_value_error_full(self) -> None:
        """Short salt also raises in hash_telegram_id_full."""
        with pytest.raises(ValueError, match="at least 16 characters"):
            hash_telegram_id_full(12345, SHORT_SALT)

    def test_exactly_16_chars_accepted(self) -> None:
        """Salt of exactly 16 characters is accepted (boundary)."""
        salt_16 = "0123456789abcdef"
        result = hash_telegram_id(12345, salt_16)
        assert len(result) == 16

    def test_empty_salt_raises(self) -> None:
        """Empty salt raises ValueError."""
        with pytest.raises(ValueError, match="at least 16 characters"):
            hash_telegram_id(12345, "")


# ── hash_telegram_id_full tests ────────────────────────────────────────────


class TestHashTelegramIdFull:
    """Tests for hash_telegram_id_full (64-char dedup hash)."""

    def test_returns_64_char_string(self) -> None:
        """hash_telegram_id_full returns exactly 64 characters."""
        result = hash_telegram_id_full(12345, TEST_SALT)
        assert len(result) == 64

    def test_returns_hex_string(self) -> None:
        """hash_telegram_id_full returns only hex characters."""
        result = hash_telegram_id_full(12345, TEST_SALT)
        assert re.fullmatch(r"[0-9a-f]{64}", result) is not None

    def test_deterministic(self) -> None:
        """Same input + salt always produces the same output."""
        result1 = hash_telegram_id_full(12345, TEST_SALT)
        result2 = hash_telegram_id_full(12345, TEST_SALT)
        assert result1 == result2

    def test_first_16_chars_match_short_hash(self) -> None:
        """The first 16 chars of the full hash match hash_telegram_id."""
        short_hash = hash_telegram_id(12345, TEST_SALT)
        full_hash = hash_telegram_id_full(12345, TEST_SALT)
        assert full_hash[:16] == short_hash

    def test_different_ids_produce_different_full_hashes(self) -> None:
        """Different Telegram IDs produce different full hashes."""
        hash1 = hash_telegram_id_full(12345, TEST_SALT)
        hash2 = hash_telegram_id_full(67890, TEST_SALT)
        assert hash1 != hash2
