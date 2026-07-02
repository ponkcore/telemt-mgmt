---
id: TKT-004
type: ticket
status: ready
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-002@0.1.0, TKT-003@0.1.0]
estimate: M
created: 2026-07-02
---

# TKT-004@0.1.1: Bot Package — aiogram Router with Proxy Link Flow

## §1 Goal

Implement the embeddable aiogram Router that handles the "Get Proxy" user flow: user presses button → system creates telemt user → returns proxy link.

## §2 In Scope

- `telemt_proxy/router.py` — `create_router(telemt_client, db_session_factory, config, tier_service=None) -> aiogram.Router` with handlers:
  - `/start` or callback "get_proxy" → hash Telegram ID → check if user exists in DB → if not, create via TelemtClient → build proxy link → generate QR code → send link + QR code to user.
  - Inline keyboard with "Получить прокси" button.
  - R18 extension point: `create_router()` accepts optional `tier_service=None` parameter (documented, not implemented). When `None`, all users receive the same server-level ad_tag.
- `telemt_proxy/hashing.py` — `hash_telegram_id(telegram_id: int, salt: str) -> str`.
- `telemt_proxy/link.py` — `build_proxy_link(server: str, port: int, secret: str) -> str`.
- `telemt_proxy/qr.py` — `generate_qr(link: str) -> bytes` (PNG image of the proxy link QR code).
- `telemt_proxy/config.py` — `ProxyConfig` dataclass for router config (server, port, salt).
- Tests: `tests/test_router.py`, `tests/test_hashing.py`, `tests/test_link.py`, `tests/test_qr.py`.

## §3 NOT In Scope

- Admin commands (TKT-005@0.1.0 API handles admin functions).
- Standalone bot entry point (TKT-006@0.1.0).
- User tier logic (R18 extension point only — `tier_service` parameter exists but no implementation).

## §4 Inputs

- ARCH-001@0.1.1 §3 C1 (Router interface, link builder, hashing, QR generation)
- ADR-001@0.1.0 (embeddable package architecture)
- ADR-005@0.1.0 (user ID hashing strategy)

## §5 Outputs

- `telemt_proxy/router.py`
- `telemt_proxy/hashing.py`
- `telemt_proxy/link.py`
- `telemt_proxy/qr.py`
- `telemt_proxy/config.py`
- `tests/test_router.py`
- `tests/test_hashing.py`
- `tests/test_link.py`
- `tests/test_qr.py`

## §6 Acceptance Criteria

- [ ] AC1 — `create_router()` returns an `aiogram.Router` with no module-level side effects (INV-EMBED).
- [ ] AC2 — `hash_telegram_id(12345, "test_salt")` returns a deterministic 16-char hex string.
- [ ] AC3 — `build_proxy_link("proxy.example.com", 443, "ee...")` returns `tg://proxy?server=proxy.example.com&port=443&secret=ee...`.
- [ ] AC4 — Router handler creates a telemt user via `TelemtClient.create_user()` on first interaction.
- [ ] AC5 — Router handler returns existing link (from DB) on subsequent interactions by same Telegram user (deduplication via `telegram_id_hash`).
- [ ] AC6 — No raw Telegram IDs stored in DB or sent to telemt (INV-HASH).
- [ ] AC7 — Link uses domain name in `server=` field (INV-DOMAIN).
- [ ] AC8 — `mypy --strict` passes.
- [ ] AC9 — Tests achieve ≥80% coverage on router.py, hashing.py, link.py, qr.py.
- [ ] AC10 — Router sends QR code image (PNG) alongside proxy link. `generate_qr()` returns valid PNG bytes for a given link.
- [ ] AC11 — `create_router()` signature includes optional `tier_service=None` parameter, documented as R18 extension point for future user-tier routing.

## §7 Constraints

- `qrcode[pil]` dependency (added in TKT-001@0.1.1). aiogram already in TKT-001@0.1.1.

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 architect: patched per RV-ARCH-001 findings M1 (QR code generation restored), M6 (R18 extension point tier_service AC added).
