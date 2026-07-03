"""Telegram ID hashing — the ONLY place this computation happens.

Per ADR-005@0.1.0 and INV-HASH:
    - User identifiers in telemt are ``sha256(str(telegram_id) + salt)[:16]``
      — never raw Telegram IDs.
    - This module is the single source of truth for this computation.
    - All other code must call ``hash_telegram_id()``.

The 16-char hex truncation is used as the telemt username (the ``name``
field in the telemt API). The full 64-char SHA256 hex digest is stored
in the ``telegram_id_hash`` column of ``proxy_users`` for deduplication
— same Telegram user pressing "Get Proxy" twice gets the same link
without storing the raw Telegram ID.
"""

from __future__ import annotations

import hashlib


def hash_telegram_id(telegram_id: int, salt: str) -> str:
    """Hash a Telegram user ID to a 16-char hex telemt username.

    Computes ``sha256(str(telegram_id) + salt)`` and returns the first
    16 characters of the hex digest. This value is used as the telemt
    API username (the ``name`` field in POST /v1/users).

    This is the ONLY function that performs this computation (ADR-005).
    All other code must call this function — never inline the hash.

    Args:
        telegram_id: The raw Telegram user ID (an integer).
        salt: The hashing salt (env var ``HASHING_SALT``). Must be at
            least 16 characters. Must never change once set.

    Returns:
        A 16-character hex string (e.g. ``"a1b2c3d4e5f6a7b8"``).

    Raises:
        ValueError: If ``salt`` is fewer than 16 characters.
    """
    if len(salt) < 16:
        raise ValueError(
            f"Salt must be at least 16 characters, got {len(salt)}"
        )
    full_hash = hashlib.sha256(
        (str(telegram_id) + salt).encode(),
    ).hexdigest()
    return full_hash[:16]


def hash_telegram_id_full(telegram_id: int, salt: str) -> str:
    """Hash a Telegram user ID to the full 64-char SHA256 hex digest.

    The full hash is stored in the ``telegram_id_hash`` column of
    ``proxy_users`` for deduplication. It allows identifying the same
    Telegram user across multiple interactions without storing the raw
    Telegram ID.

    Args:
        telegram_id: The raw Telegram user ID (an integer).
        salt: The hashing salt (env var ``HASHING_SALT``).

    Returns:
        A 64-character hex string (the full SHA256 digest).

    Raises:
        ValueError: If ``salt`` is fewer than 16 characters.
    """
    if len(salt) < 16:
        raise ValueError(
            f"Salt must be at least 16 characters, got {len(salt)}"
        )
    return hashlib.sha256(
        (str(telegram_id) + salt).encode(),
    ).hexdigest()
