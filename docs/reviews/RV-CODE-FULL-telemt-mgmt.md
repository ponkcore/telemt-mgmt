# RV-CODE-005: Full Project Audit — telemt-mgmt

| Field         | Value                                                      |
|---------------|-------------------------------------------------------------|
| Review ID     | RV-CODE-005                                                 |
| Commit        | `9c85a49` (TKT-019: close cycle)                           |
| Scope         | Full project audit — all 205 files, 8 review areas          |
| Reviewer      | Viktor (AI)                                                 |
| Date          | 2026-07-04                                                  |
| Verdict       | **Conditional pass** — 2 High, 6 Medium, 7 Low findings    |

---

## Area summary

| # | Area                      | Verdict  | Findings |
|---|---------------------------|----------|----------|
| 1 | Code quality              | ⚠ WARN   | H1, M1, M2, L1 |
| 2 | Security                  | ⚠ WARN   | H2, M3   |
| 3 | Infrastructure            | ⚠ WARN   | M4, M5, L2 |
| 4 | Frontend                  | ✅ PASS   | L3       |
| 5 | Test coverage             | ✅ PASS   | L4       |
| 6 | Architecture compliance   | ⚠ WARN   | M6, L5   |
| 7 | Documentation consistency | ⚠ WARN   | L6, L7   |
| 8 | Operational readiness     | ✅ PASS   | —        |

---

## Findings

### H1 · High — Blocking calls in async handlers violate INV-ASYNC

**Files:**
- `api/auth.py:58` — `bcrypt.checkpw()` in `verify_password()`
- `api/auth.py:62` — `bcrypt.hashpw()` in `get_password_hash()`
- `telemt_proxy/qr.py:17-30` — `qr.make()` + `img.save()` in `generate_qr()`

**Problem:** `bcrypt.checkpw` and `bcrypt.hashpw` are intentionally CPU-intensive (12 rounds ≈ 200-400 ms). They're called directly from async route handlers (`POST /api/auth/login`). This blocks the asyncio event loop, stalling all concurrent requests during password verification.

Similarly, `generate_qr()` performs synchronous CPU-bound QR code generation (matrix calculation + PNG encoding) and is called from the async bot handler `_handle_get_proxy` in `router.py`.

INV-ASYNC (`.opencode/project.jsonc`): *"All I/O and CPU-bound work MUST be async or wrapped in asyncio.to_thread()."*

**Fix:**
```python
# api/auth.py
async def verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(bcrypt.checkpw, plain.encode(), hashed.encode())

async def get_password_hash(password: str) -> str:
    return await asyncio.to_thread(
        lambda: bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    )

# telemt_proxy/qr.py — wrap in to_thread at call site or make async
qr_bytes = await asyncio.to_thread(generate_qr, link)
```

---

### H2 · High — JWT secret defaults to a public, guessable value (INV-SECRETS)

**File:** `api/deps.py:14`

```python
JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
```

**Problem:** If `JWT_SECRET_KEY` is not set in the environment, the fallback `"dev-secret-change-me"` is used. This string is committed to the public repository. Anyone who reads the source can forge valid admin JWTs — complete auth bypass.

The `deploy-mgmt.sh` script auto-generates and injects `JWT_SECRET_KEY`, so production deploys via the script are safe. But:
1. A manual deploy that skips the script (e.g. `docker compose up` directly) silently uses the insecure default.
2. The default violates INV-SECRETS: *"All secrets via env vars or .env; no hardcoded secrets."*

**Fix:** Remove the default; raise on startup if missing:
```python
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be set — see .env.example")
```

---

### M1 · Medium — `telemt_proxy/database.py` has module-level side effects (INV-EMBED)

**File:** `telemt_proxy/database.py:1-20`

```python
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, ...)
```

**Problem:** Importing `telemt_proxy` (or anything that imports `.database`) immediately creates a SQLAlchemy async engine from `DATABASE_URL`. This violates INV-EMBED: *"telemt_proxy/ is a library package. No module-level side effects, no global state. All dependencies injected via create_router()."*

Consequences:
1. Embedding `telemt_proxy` in an existing bot that has its own database engine fails — the import triggers a second engine creation with potentially the wrong `DATABASE_URL`.
2. The `bot/main.py:setup_bot()` correctly creates its own engine, but `api/deps.py:get_db_session` re-exports from the module-level factory, creating a divergence.
3. Tests must set `DATABASE_URL` before importing any module (the `conftest.py` does this, masking the issue).

**Fix:** Convert to a factory function:
```python
def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```
Then inject the factory in `api/main.py:create_app()` and `bot/main.py:setup_bot()`.

---

### M2 · Medium — Exit Xray `xver:1` may produce double PROXY protocol headers

**File:** `infra/exit/xray-config.json.template:22`

```json
"realitySettings": {
    "xver": 1,
    ...
}
```

**Problem:** The entry server's inbound sets `xver: 1`, which prepends a PROXYv1 header containing the real client IP into the VLESS tunnel. The exit server's inbound also has `xver: 1`, which prepends *another* PROXYv1 header (with the *entry server's* IP) when forwarding to telemt on `:8443`.

telemt receives: `[PROXY hdr: entry_IP]` + `[PROXY hdr: client_IP]` + `[MTProto data]`

telemt's `proxy_protocol = true` parses only the first header, so it sees the *entry server's IP* as the client — defeating client IP preservation entirely. Worse, the second PROXY header bytes are then parsed as MTProto, likely causing connection failures.

ARCH-001 §3 C7 states: *"C7 forwards this header as-is to telemt"* — the exit should not add its own.

**Impact:** Client IP tracking is broken (all users appear from entry server IP), and connections may fail outright.

**Fix:** Change exit template to `"xver": 0` — the exit should forward the entry's PROXY header without adding its own:
```json
"xver": 0,
```

**Note:** I cannot confirm runtime behaviour without a live environment. If telemt strips the outer PROXY header and correctly reads the inner one, the impact is lower. But per Xray documentation, `xver:1` on the inbound *always* prepends a new header. Verify with a live test.

---

### M3 · Medium — CORS allows only `PANEL_DOMAIN` but `/api/auth/login` has no CSRF protection

**File:** `api/main.py:49-56`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Problem:** CORS is configured with `allow_credentials=True` and `allow_methods=["*"]`, `allow_headers=["*"]`. While `allow_origins` is locked to the panel domain, the wildcard methods/headers are overly permissive. More importantly, there is no CSRF token on the login form. Since the JWT is stored in `localStorage` (not httpOnly cookies), CSRF is not exploitable for authenticated requests — but the login endpoint itself could be targeted by a cross-origin POST from a malicious site (credential stuffing via CORS preflight bypass for simple requests).

**Impact:** Low in practice (rate limiter mitigates brute-force), but tightening CORS is best practice.

**Fix:** Restrict `allow_methods` to `["GET", "POST", "DELETE", "OPTIONS"]` and `allow_headers` to `["Authorization", "Content-Type"]`.

---

### M4 · Medium — `.env.example` files are stale after TKT-014/TKT-018/TKT-019

**Files:**
- `infra/entry/.env.example:9` — `REALITY_SNI=yahoo.com` but deploy script defaults to `ads.x5.ru`
- `infra/exit/.env.example:17` — `TLS_DOMAIN=github.com` but deploy script defaults to `www.microsoft.com`
- `infra/entry/.env.example` — missing encrypted S2 variables (`EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`) added by TKT-018
- `infra/exit/.env.example` — missing exit Xray variables (`EXIT_VLESS_UUID`, `EXIT_REALITY_PRIVATE_KEY`, `EXIT_REALITY_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_REALITY_SHORT_IDS`) added by TKT-018

**Problem:** An operator reading `.env.example` as documentation gets wrong defaults and misses required variables. The deploy scripts work correctly (they prompt), but the `.env.example` files — the primary documentation for operators — are outdated.

**Fix:** Update both `.env.example` files to match current deploy scripts:
- Entry: change `REALITY_SNI` default to `ads.x5.ru`, add exit-related variables
- Exit: change `TLS_DOMAIN` default to `www.microsoft.com`, add exit Reality variables

---

### M5 · Medium — `migrate.sh` health check uses HTTPS, fails for entry servers

**File:** `scripts/migrate.sh:280`

```bash
if curl -sf --connect-timeout 5 --max-time 10 "https://${DOMAIN}" >/dev/null 2>&1; then
```

**Problem:** After migrating an *entry* server, the health check calls `https://${DOMAIN}`. Entry servers run VLESS-Reality on `:443` — they don't serve standard HTTPS. `curl` will fail the TLS handshake because Reality uses a fake TLS layer, causing the health check to always fall back to the Docker status check (SSH-based).

The fallback works, but the primary check (AC5) is effectively dead for half the server types.

**Fix:** Differentiate by `$SERVER_TYPE`:
```bash
if [[ "$SERVER_TYPE" == "exit" ]]; then
    HEALTH_URL="http://${DOMAIN}:8080"  # Angie mask host
else
    # Entry servers don't serve HTTP(S) — check via SSH/docker
    HEALTH_CHECK_OK=false
    # ... skip curl, go straight to docker check
fi
```

---

### M6 · Medium — `ProxyConfig` has 5 fields but ArchSpec documents 3

**Files:**
- `telemt_proxy/config.py:1-20` — `ProxyConfig(server, port, salt, auth_header, base_url)`
- `docs/architecture/ARCH-001-telemt-mgmt.md` §3 C1 — documents `ProxyConfig(server: str, port: int, salt: str)`

**Problem:** `ProxyConfig` grew two fields (`auth_header`, `base_url`) during implementation but the ArchSpec was not updated. This makes the ArchSpec misleading for anyone trying to embed the package — they'd miss required config fields.

**Fix:** Update ARCH-001 §3 C1 to document all 5 fields of `ProxyConfig`, or refactor to inject `TelemtClient` separately so `ProxyConfig` stays at the 3 documented fields (which is what `create_router()` already does — it takes `telemt_client` as a separate parameter, making `auth_header` and `base_url` on `ProxyConfig` redundant).

---

### L1 · Low — `telemt_proxy/qr.py` uses `kind` parameter for PIL `save()`

**File:** `telemt_proxy/qr.py:28`

```python
img.save(buffer, kind="PNG")
```

**Problem:** Pillow's `Image.save()` accepts `format=` not `kind=`. The `qr.make_image()` returns a `StyledPilImage` from the `qrcode` library, whose `.save()` method does accept `kind=` as an alias. This works at runtime via `qrcode`'s wrapper, but is non-standard and would break if the image were a raw PIL `Image` object. Tests pass because they use `qrcode`'s `StyledPilImage`.

**Impact:** None at runtime. Stylistic inconsistency.

---

### L2 · Low — Exit `docker-compose.yml` comment says "PROXYv2" but `xver:1` is PROXYv1

**File:** `infra/entry/docker-compose.yml:6` (comment)

The entry `docker-compose.yml` header comment references `PROXYv2`, but the Xray config template uses `"xver": 1` which is PROXYv1 (text-based). PROXYv2 would be `"xver": 2` (binary).

**Impact:** Documentation-only. The code is correct (PROXYv1 is the intended protocol per ARCH-001 §3 C5).

**Fix:** Update the comment to say "PROXYv1".

---

### L3 · Low — Frontend stores JWT in `localStorage` (XSS-accessible)

**File:** `frontend/src/api/client.ts:4`

```typescript
const TOKEN_KEY = "telemt_admin_token";
localStorage.setItem(TOKEN_KEY, res.data.access_token);
```

**Problem:** JWT is stored in `localStorage`, which is accessible to any JavaScript on the page. If an XSS vulnerability exists (e.g. via a browser extension, compromised CDN, or future code change), the token can be stolen.

**Impact:** Low — React auto-escapes all JSX output, there are no `dangerouslySetInnerHTML` calls, and the panel is a private admin tool. ADR-002 explicitly permits localStorage.

**Recommendation:** For a future hardening pass, consider `httpOnly` cookies with `SameSite=Strict`.

---

### L4 · Low — No integration tests for deploy scripts

**Problem:** All 5 deploy scripts (`deploy-exit.sh`, `deploy-entry.sh`, `deploy-mgmt.sh`, `deploy-monitoring.sh`, `deploy-landing.sh`) and the migration script are untested. While they're operationally validated, a typo in a `sed` substitution or a missed variable could silently produce broken configs.

**Impact:** Low — the scripts are mature and follow a consistent pattern. Manual testing covers the happy path.

**Recommendation:** Add a CI smoke test that runs each deploy script with a mock `.env` and validates the generated config files (config.toml, xray-config.json, angie.conf) contain expected values.

---

### L5 · Low — Admin-created links bypass `hash_telegram_id()` for `telegram_id_hash`

**File:** `api/routes/links.py:38-44`

```python
telemt_username = hashlib.sha256(body.label.encode()).hexdigest()[:16]
# ...
proxy = ProxyUser(
    telemt_username=telemt_username,
    telegram_id_hash=hashlib.sha256(body.label.encode()).hexdigest(),
    source="admin_label",
)
```

**Problem:** Admin-created labelled links hash the *label* (not a Telegram ID) to create both `telemt_username` and `telegram_id_hash`. This bypasses `hash_telegram_id()` and doesn't use the `HASHING_SALT`. The `telegram_id_hash` column stores a hash of the label, not a Telegram ID hash — semantically misleading.

This is **by design** (admin links have no Telegram ID), but the code doesn't document why it diverges from INV-HASH, and the column name `telegram_id_hash` is misleading for admin-sourced records.

**Impact:** None — admin links work correctly. The salt omission is acceptable since labels are not PII.

**Recommendation:** Add a code comment explaining the intentional divergence, and consider renaming the field to `identity_hash` in a future migration.

---

### L6 · Low — Entry `docker-compose.yml` missing `ulimits` (inconsistent with exit)

**File:** `infra/entry/docker-compose.yml`

**Problem:** The exit `docker-compose.yml` sets `ulimits: nofile: soft: 65536, hard: 262144` on the telemt service, matching ARCH-001 §3 C5 / knowledge report §7.5. The entry `docker-compose.yml` does not set `ulimits` on the Xray service.

**Impact:** Low — Xray's default ulimits are typically sufficient for a relay, and the entry handles far fewer file descriptors than the exit. But inconsistency with the exit compose file could confuse operators.

---

### L7 · Low — `README.md` and `CONTRIBUTING.md` not reviewed for staleness

I did not find significant drift in the README or CONTRIBUTING.md relative to the current codebase. Both reference the correct commands (`make test`, `make lint`, `make typecheck`) and project structure. Minor: the README could mention the landing page deploy (`infra/landing/`).

---

## Positive observations

1. **Excellent async architecture.** `TelemtClient` is a well-designed async httpx wrapper with proper context management, typed returns via Pydantic models, and comprehensive error mapping. The 4-exception hierarchy (`TelemtAPIError` → `TelemtAuthError` / `TelemtNotFoundError` / `TelemtConnectionError`) is clean and well-tested.

2. **Strong test suite.** 12 test files with ~120 tests covering all API endpoints, the client library, bot lifecycle, hashing, link building, QR generation, ORM models, and the router. `respx` mocking is used consistently and correctly. The `conftest.py` fixture composition (engine → session factory → session → app → client) is exemplary.

3. **Docker hardening is thorough.** Every compose file across all 5 infrastructure roles consistently applies `cap_drop: ALL`, `read_only: true`, `security_opt: no-new-privileges:true`, and adds back only `NET_BIND_SERVICE` where needed. This exceeds the typical standard for infrastructure projects.

4. **Deploy scripts are production-grade.** The idempotent re-run pattern (`load_env` → `prompt_for` → `save_env_var`) is consistent across all 5 scripts. Error handling is thorough with `set -euo pipefail`. Timing wrappers, banner formatting, and operator-facing output are polished.

5. **Self-steal domain support is well-engineered.** The ADR-010 implementation in `deploy-exit.sh` handles domain detection, DNS verification, Let's Encrypt cert acquisition, cert path mapping into Docker volumes, and port conflict warnings — all idempotently. The alternative Angie templates (standard, SNI router, self-steal) are well-documented.

6. **Embeddable package pattern works.** Despite the `database.py` module-level issue (M1), the `create_router()` factory pattern with `TierServiceProtocol` dependency injection is well-designed. The 3-line integration example is real and tested.

7. **Migration script is comprehensive.** 8-step migration cycle with tar backup, SCP transfer, Cloudflare DNS update, health check, rollback instructions, and verification commands. All within a ~2-minute downtime target.

8. **Frontend is clean and functional.** TypeScript strict mode, typed API client matching Python schemas, proper auth guard routing, dark theme with sidebar layout. No `any` types, no `dangerouslySetInnerHTML`.

---

## Invariant compliance matrix

| Invariant       | Status | Notes |
|-----------------|--------|-------|
| INV-AUTH        | ✅ PASS | TelemtClient sets auth_header on every request |
| INV-SECRETS     | ⚠ H2   | JWT_SECRET_KEY defaults to public string |
| INV-HASH        | ✅ PASS | Single hash function; admin links intentionally diverge (L5) |
| INV-DOMAIN      | ✅ PASS | All proxy links use FQDN, never raw IP |
| INV-TIMEOUT     | ✅ PASS | All httpx clients have explicit timeouts |
| INV-ORM         | ✅ PASS | No raw SQL; all queries via SQLAlchemy ORM + Alembic ops |
| INV-EMBED       | ⚠ M1   | `database.py` module-level engine creation |
| INV-IDEMPOTENT  | ✅ PASS | All deploy scripts load .env and skip existing values |
| INV-DOCKER      | ✅ PASS | All containers hardened: cap_drop, read_only, no-new-privileges |
| INV-ASYNC       | ⚠ H1   | bcrypt and QR generation block the event loop |

---

## Prioritised recommendations

1. **[H1] Wrap bcrypt and QR calls in `asyncio.to_thread()`.** Straightforward fix; prevents event loop starvation under concurrent login or proxy requests.

2. **[H2] Remove `JWT_SECRET_KEY` default; fail fast if unset.** One-line change that closes a potential auth bypass.

3. **[M2] Set exit Xray `xver: 0`.** Verify in a staging environment first, then update the template. This may already be causing silent client IP loss in production.

4. **[M1] Refactor `database.py` to a factory function.** Needed to truly satisfy INV-EMBED for third-party bot embedding.

5. **[M4] Update `.env.example` files.** Quick documentation fix to prevent operator confusion.

6. **[M5] Fix `migrate.sh` health check for entry servers.** Small conditional change.

7. **[M3] Tighten CORS wildcards.** Restrict `allow_methods` and `allow_headers` to only what's needed.

8. **[M6] Align ArchSpec with `ProxyConfig` reality.** Update ARCH-001 or refactor to remove redundant fields.
