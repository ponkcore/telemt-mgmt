---
id: TKT-007
type: ticket
status: in_review
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-005@0.1.0]
estimate: L
created: 2026-07-02
---

# TKT-007@0.1.1: Admin Web Panel — React + TypeScript Frontend

## §1 Goal

Implement the admin web panel as a React + TypeScript SPA consuming the FastAPI admin API.

## §2 In Scope

- Login page (username/password form → JWT).
- Dashboard page (stats overview: active users, total traffic, connections; Grafana iframe or link to external Grafana; "Promotion" card linking to @MTProxybot stats URL (t.me/MTProxybot) for M6 ad_tag attribution).
- Users page (table with search, disable/enable buttons, pagination).
- Links page (create labelled link form, list with copy-to-clipboard, delete).
- Layout: dark theme sidebar navigation, card-based layout, following Remnawave's visual patterns.
- API client module with JWT token management (auto-refresh, redirect to login on 401).
- Responsive design (works on tablet+).

## §3 NOT In Scope

- User-facing pages (end users don't access the panel — PRD Non-Goal).
- Settings page for modifying telemt config (config managed via deploy scripts).
- Real-time WebSocket updates (polling in MVP).
- Internationalisation (Russian only in MVP).

## §4 Inputs

- ARCH-001@0.1.1 §3 C4 (Panel interface/contract)
- ARCH-001@0.1.1 §3 C3 (Admin API contract — all endpoints)
- ARCH-001@0.1.1 §8 (Observability — M6 attribution @MTProxybot promotion card)
- ADR-002@0.1.0 (JWT auth — frontend handles 401, stores token)

## §5 Outputs

- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Users.tsx`
- `frontend/src/pages/Links.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/StatsCard.tsx`
- `frontend/src/components/UserTable.tsx`
- `frontend/src/components/LinkForm.tsx`
- `frontend/src/styles/global.css`
- `frontend/index.html`

## §6 Acceptance Criteria

- [ ] AC1 — Login page authenticates via `POST /api/auth/login` and stores JWT.
- [ ] AC2 — Dashboard shows active users count, total connections, total traffic from `GET /api/stats`.
- [ ] AC3 — Users page lists users with pagination from `GET /api/users`.
- [ ] AC4 — Links page allows creating a labelled link via `POST /api/links` and displays the `tg://proxy` link with copy button.
- [ ] AC5 — 401 API responses redirect to login page.
- [ ] AC6 — Dark theme with sidebar navigation.
- [ ] AC7 — `npx tsc --noEmit` passes.
- [ ] AC8 — `npx eslint src` passes.
- [ ] AC9 — Admin panel loads user list with 1000+ users in <2 seconds (M4 — API response time, not frontend rendering).
- [ ] AC10 — Dashboard includes a link/card to @MTProxybot promotion stats (t.me/MTProxybot) for M6 ad_tag attribution.

## §7 Constraints

- Authorised new frontend dependencies: react-router-dom, axios (or fetch), @tanstack/react-query (optional).
- No TailwindCSS (vanilla CSS per project conventions unless PO requests otherwise).

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 architect: patched per RV-ARCH-001 finding L3 (@MTProxybot promotion card added to dashboard for M6 attribution).
- 2026-07-03 executor: implemented all §5 Outputs. AC1-AC10 met. tsc/eslint/build/validate_docs all green. PR opened.
