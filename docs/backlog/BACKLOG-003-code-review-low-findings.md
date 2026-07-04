---
id: BACKLOG-003
type: backlog
status: open
source: RV-CODE-FULL-telemt-mgmt.md
created: 2026-07-04
---

# BACKLOG-003: Low findings from comprehensive code review

## Items

### L1 — qr.py uses `kind=` instead of `format=` for PIL save
- File: `telemt_proxy/qr.py:28`
- Impact: None (qrcode's StyledPilImage accepts `kind=`). Stylistic.

### L2 — Entry docker-compose comment says PROXYv2 but code uses PROXYv1
- File: `infra/entry/docker-compose.yml:6`
- Fix: Update comment to "PROXYv1"

### L3 — JWT stored in localStorage (XSS-accessible)
- File: `frontend/src/api/client.ts:4`
- Impact: Low (React escapes output, no dangerouslySetInnerHTML). ADR-002@0.1.0 permits.
- Future: Consider httpOnly cookies with SameSite=Strict

### L4 — No integration tests for deploy scripts
- Fix: Add CI smoke test that runs scripts with mock .env and validates generated configs

### L5 — Admin-created links bypass hash_telegram_id() for telegram_id_hash
- File: `api/routes/links.py:38-44`
- By design (admin links have no TG ID), but code doesn't document why
- Future: Consider renaming column to `identity_hash`

### L6 — Entry docker-compose missing ulimits (inconsistent with exit)
- File: `infra/entry/docker-compose.yml`
- Impact: Low (Xray defaults sufficient for relay)

### L7 — README could mention landing page deploy
- Minor documentation gap

### L8 — .env.example EXIT_REALITY_SNI default stale (from RV-CODE-024-1 F-L1)
- File: `infra/exit/.env.example`
- Impact: `.env.example` still shows `EXIT_REALITY_SNI=www.microsoft.com` but `deploy-exit.sh` default is now `ads.x5.ru` (TKT-024@0.2.1 N4 fix).
- Fix: Update `.env.example` to `EXIT_REALITY_SNI=ads.x5.ru` in a future doc/infra PR.
