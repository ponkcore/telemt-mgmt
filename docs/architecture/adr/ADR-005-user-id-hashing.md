---
id: ADR-005
type: adr
status: accepted
created: 2026-07-02
---

# ADR-005: User ID Hashing Strategy

## Context

PRD-001@0.3.0 §5 R16 mandates that user identifiers in telemt are `sha256(telegram_id + salt)[:16]` — never raw Telegram IDs. ARCH-001@0.1.0 §5 INV-HASH defines this as a cross-cutting invariant.

## Decision

We will implement a single function `telemt_proxy.hashing.hash_telegram_id(telegram_id: int, salt: str) -> str` that:
1. Computes `sha256(str(telegram_id) + salt)` using Python's `hashlib.sha256`.
2. Returns the first 16 characters of the hex digest.
3. This is the ONLY function that performs this computation — all other code calls it.

The `salt` is an env var (`HASHING_SALT`) set during deploy. The salt:
- Must be at least 16 characters.
- Is NOT a secret per se (it's not a key) but provides pseudonymity — without the salt, a Telegram ID cannot be mapped to a telemt username.
- Once set, must NEVER change (changing it would orphan all existing telemt users).

The database stores both `telemt_username` (16-char hash, used as telemt API username) and `telegram_id_hash` (full 64-char sha256, used for deduplication — same Telegram user pressing "Get Proxy" twice gets the same link).

## Consequences

- **Positive:** No raw Telegram IDs in telemt or our database. Privacy by design.
- **Positive:** Deduplication works without storing Telegram IDs.
- **Negative / cost:** Salt management adds operational complexity. Lost salt = cannot correlate existing users.
- **Follow-ups:** `deploy-mgmt.sh` auto-generates a salt if not provided and stores it in `.env`. Backup of `.env` is critical.

## Alternatives considered

- **Random username (UUID4)** — rejected because deduplication requires mapping Telegram ID → username, which needs a deterministic function.
- **HMAC-SHA256 with a secret key** — considered; sha256+salt is simpler and sufficient for pseudonymity (not authentication).
