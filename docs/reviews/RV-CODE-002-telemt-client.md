---
id: RV-CODE-002
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/3"
ticket_ref: TKT-002@0.1.0
status: in_review
verdict: pass
created: 2026-07-02
---

# RV-CODE-002: review of TKT-002 — TelemtClient (PR #3)

**Verdict:** pass
**Summary:** TelemtClient meets the ARCH-001@0.1.2 §3 C1 contract, ADR-004@0.1.1 wrapper requirements, and all verifiable acceptance criteria; tests pass with 100% client.py coverage, mypy --strict is clean, and no scope or invariant violations were found.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (`telemt_proxy/client.py`, `telemt_proxy/exceptions.py`, `telemt_proxy/schemas.py`, `tests/test_client.py`) plus ticket status/§10.
- [x] No §3 NOT-In-Scope term touched (no DB models, bot Router handlers, admin API endpoints, or `PATCH /v1/config`).
- [x] No unauthorised runtime dependency (httpx/pydantic already declared in TKT-001@0.1.1; respx already in dev group).
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (mypy --strict, ruff, pytest coverage, validate_docs).
- [x] All relevant project.jsonc invariants hold (INV-AUTH, INV-TIMEOUT, INV-ASYNC).

## Acceptance criteria

| AC | Requirement | Evidence | Status |
|---|---|---|---|
| AC1 | All 9 methods implemented | `telemt_proxy/client.py:193-310` — `create_user`, `list_users`, `get_user`, `disable_user`, `enable_user`, `rotate_secret`, `get_stats_summary`, `get_active_ips`, `get_connections_summary` | ✓ |
| AC2 | Methods return typed Pydantic models | `create_user`→`TelemtUser`, `list_users`→`list[TelemtUser]`, `get_user`→`TelemtUser`, `get_stats_summary`→`TelemtStats`, `get_active_ips`/`get_connections_summary`→`list[TelemtConnection]` (`client.py:206,218,233,284,297,310`) | ✓ |
| AC3 | `async with TelemtClient(...) as client:` works | `__aenter__`/`__aexit__` at `client.py:82-100`; tests `test_context_manager_lifecycle`, `test_lazy_client_without_context_manager` | ✓ |
| AC4 | Explicit timeouts: 10s connect, 30s read | `DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, ...)` at `client.py:41`; tests `test_default_timeout_is_10s_connect_30s_read` | ✓ |
| AC5 | `auth_header` sent as `Authorization` on every request | `headers={"Authorization": self._auth_header}` at `client.py:87,114`; tests `test_auth_header_sent_on_every_request`, `test_auth_header_sent_on_post` | ✓ |
| AC6 | Correct exception mapping | `_handle_error` at `client.py:118-145`; tests for 401/403→`TelemtAuthError`, 404→`TelemtNotFoundError`, `ConnectError`/`HTTPError`→`TelemtConnectionError`, 500→`TelemtAPIError` | ✓ |
| AC7 | `mypy --strict` passes | `uv run mypy --strict telemt_proxy/client.py telemt_proxy/exceptions.py telemt_proxy/schemas.py` → "Success: no issues found in 3 source files" | ✓ |
| AC8 | ≥80% coverage on `client.py` | `uv run pytest tests/test_client.py -q --cov=telemt_proxy.client --cov-report=term-missing` → 83 statements, 0 miss, 100% | ✓ |

## Findings

### High (block merge)
- None.

### Medium (fix or backlog)
- None.

### Low (optional)
- **F-L1 — AC2 wording overreach**: The ticket states "All methods return typed Pydantic models", but `disable_user` and `enable_user` return `None`, and `rotate_secret` returns `str`. This is the correct behavior for the underlying telemt API contract (these endpoints either have no body or return only a secret string), but the AC should ideally read "all response-bearing methods" or be reworded in a future ticket revision.
- **F-L2 — lazy client convenience is undocumented**: `_get_client` (`client.py:104-116`) permits using `TelemtClient` without `async with`. It is tested and harmless, but it extends the ADR-004@0.1.1 contract; consider documenting it explicitly or removing it if strict context-manager-only usage is desired.

## Red-team probes
- **error_paths**: Mapped comprehensively — `httpx.ConnectError` and other `httpx.HTTPError` subclasses map to `TelemtConnectionError`; 401/403→`TelemtAuthError`; 404→`TelemtNotFoundError`; other status errors→`TelemtAPIError`. Test coverage includes all paths. ✓
- **concurrency**: `httpx.AsyncClient` is reused within a context; no shared mutable state beyond the client reference. N/A beyond current scope.
- **input_validation**: Pydantic `model_validate` is used for every JSON response; username/path inputs are passed directly to f-strings — this is acceptable because telemt usernames are SHA256 hashes constrained by INV-HASH upstream. N/A for this ticket.
- **prompt_injection**: No LLM or prompt surface in this code. N/A.
- **authz_isolation**: `auth_header` is set once on the `httpx.AsyncClient` and sent on every request; no leakage or conditional auth. ✓
- **secrets**: `auth_header` is a constructor arg only; no secrets hardcoded. ✓
- **observability**: No logging/tracing added in this ticket; acceptable per scope, but consider adding structured logging in future tickets for production visibility.
- **rollback**: Client state is ephemeral; no persistent state. N/A.

## Checks executed
```bash
uv sync
uv run mypy --strict telemt_proxy/client.py telemt_proxy/exceptions.py telemt_proxy/schemas.py
uv run ruff check telemt_proxy/client.py telemt_proxy/exceptions.py telemt_proxy/schemas.py tests/test_client.py
uv run pytest tests/test_client.py -q --cov=telemt_proxy.client --cov-report=term-missing
python3 scripts/validate_docs.py
```

All commands succeeded. Coverage: 100% on `telemt_proxy/client.py`. `validate_docs`: 26 documents, 0 errors.
