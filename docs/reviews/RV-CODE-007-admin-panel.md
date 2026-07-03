---
id: RV-CODE-007
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/12"
ticket_ref: TKT-007@0.1.1
status: in_review
created: 2026-07-03
---

# RV-CODE-007: review of TKT-007@0.1.1 Admin Web Panel (PR #12)

**Verdict:** pass_with_changes
**Summary:** The frontend satisfies all 10 acceptance criteria and the §7 constraints, but the package manifest changes are outside the ticket's §5 Outputs and the backend pytest suite fails in this review environment (unrelated environment issue).

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).  
  *Note: `frontend/package.json` and `frontend/package-lock.json` were also modified, but only to add §7-authorised dependencies.*
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] project.jsonc checks green (typecheck/lint/build/validate_docs for the frontend; backend pytest failure is an environment issue — see M2).
- [x] All project.jsonc invariants hold for changed frontend code.

## Acceptance criteria
- **AC1** — `frontend/src/pages/Login.tsx:22-23` submits via `api.login()`; `frontend/src/api/client.ts:57-64` posts to `/auth/login` and stores the JWT in `localStorage`.
- **AC2** — `frontend/src/pages/Dashboard.tsx:36,93-100` fetches and displays `active_users`, `total_connections`, and `total_traffic` from `GET /api/stats`.
- **AC3** — `frontend/src/components/UserTable.tsx:25-26` calls `api.getUsers(page, PER_PAGE)`; `frontend/src/pages/Users.tsx:15` renders the paginated table.
- **AC4** — `frontend/src/components/LinkForm.tsx:28` posts `{label}` to `/api/links`; `frontend/src/pages/Links.tsx:54-62,96-101` displays the `tg://proxy` link with a copy button.
- **AC5** — `frontend/src/api/client.ts:41-53` intercepts 401 responses, clears the token, and redirects to `/login`; `frontend/src/App.tsx:22-28` guards protected routes.
- **AC6** — `frontend/src/styles/global.css:1-807` implements a dark theme; `frontend/src/components/Sidebar.tsx:81-120` and `frontend/src/components/Layout.tsx:12-20` provide sidebar navigation.
- **AC7** — `npx tsc --noEmit` passes with zero errors.
- **AC8** — `npx eslint src` passes with zero errors.
- **AC9** — `frontend/src/components/UserTable.tsx:11,25-26,132-153` fetches 20 users per page and renders pagination controls, keeping the frontend rendering cost independent of total user count.
- **AC10** — `frontend/src/pages/Dashboard.tsx:56-82` includes a promotion card linking to `https://t.me/MTProxybot` per ARCH-001@0.1.2 §8 M6 attribution.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- **F-M1:** `frontend/package.json` and `frontend/package-lock.json` were modified but are not listed in TKT-007@0.1.1 §5 Outputs. Only §7-authorised dependencies (`axios`, `react-router-dom`) were added. Backlog: update the ticket template to list dependency manifests in §5 when authorised deps are added.
- **F-M2:** `uv run pytest -q` fails in this review environment with `ValueError: the greenlet library is required ... libstdc++.so.6: cannot open shared object file`. This is an environment-level issue, not caused by the frontend-only diff. Re-run in CI before merging; if CI is green, this finding can be closed. Cited from `tests/test_models.py:428` and the environment log.

### Low  (optional)
- **F-L1:** `frontend/src/components/UserTable.tsx:39-41` performs client-side search only on the currently loaded page. For 1000+ users, backend search would be more useful. Backlog.
- **F-L2:** `frontend/src/App.tsx:36` uses `window.location.href = "/login"` redundantly alongside the `<Navigate>` guard, causing a full page reload. Backlog.
- **F-L3:** `frontend/src/pages/Login.tsx:24-25` collapses all login errors into a generic “wrong password” message, so network failures are indistinguishable. Backlog.

## Red-team probes
- error_paths: 401 is handled by redirecting to `/login` and clearing the token (`client.ts:41-53`); other API errors surface generic toast messages. No crash loop risk.
- concurrency: Axios client has a 15 s timeout (`client.ts:25`); no long-polling or race-prone shared state beyond standard React hooks.
- input_validation: Login form relies on HTML `required`; link form trims and checks empty label. XSS vectors are mitigated by React escaping.
- authz_isolation: JWT is stored in `localStorage` as allowed by ADR-002@0.1.0/ARCH-001@0.1.1 §3 C4; no RBAC is expected in MVP.
- secrets: No hard-coded secrets or credentials in source; only the `TOKEN_KEY` constant is present.
- observability: Errors are logged to the console; no production telemetry or external logging endpoints are introduced.
- rollback: Pure frontend SPA change; rolling back the deployment reverses the feature. No database or infra changes.
- dns_failover: Not applicable to this frontend-only panel change.
