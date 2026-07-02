---
id: ADR-004
type: adr
status: accepted
created: 2026-07-02
---

# ADR-004: Thin httpx Wrapper for Telemt API

## Context

ARCH-001@0.1.1 §3 C1 and C3 both need to communicate with telemt's REST API (:9091). The PO confirmed (decision fork #4) a thin wrapper approach. The project invariant INV-TIMEOUT requires explicit timeouts on all httpx clients.

## Decision

We will implement `TelemtClient` in `telemt_proxy/client.py` — an async httpx-based wrapper with:
- Typed methods for each telemt API endpoint (create_user, list_users, get_user, disable_user, enable_user, rotate_secret, get_stats_summary, get_active_ips, get_connections_summary).
- Constructor takes `base_url`, `auth_header`, `timeout` (default: 10s connect, 30s read).
- Implements `async with` context manager for httpx client lifecycle.
- Returns Pydantic models (not raw dicts) for type safety.
- Raises typed exceptions: `TelemtAPIError` (base), `TelemtConnectionError` (network), `TelemtAuthError` (401/403), `TelemtNotFoundError` (404).

## Consequences

- **Positive:** Single source of truth for auth, timeouts, error handling. Shared by bot and API.
- **Positive:** Typed return values catch integration errors at development time (mypy --strict).
- **Negative / cost:** Must be updated when telemt API changes (tight coupling to telemt version).
- **Follow-ups:** `TelemtClient` is the ONLY code that makes HTTP calls to telemt. Reviewers reject any direct httpx calls to :9091 outside this class.

## Alternatives considered

- **Raw httpx calls** — rejected; duplicated auth/timeout logic, violates INV-TIMEOUT.
- **Auto-generated from OpenAPI** — rejected; telemt has no OpenAPI spec.

## Revision Log

- 2026-07-02 0.1.1 — removed `If-Match` / `PATCH /v1/config` mention per RV-ARCH-001 finding M4. Config is managed via deploy scripts, not runtime API; the thin-wrapper scope matches TKT-002@0.1.0.
