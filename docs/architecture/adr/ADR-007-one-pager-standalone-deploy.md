---
id: ADR-007
type: adr
status: accepted
created: 2026-07-02
---

# ADR-007: One-Pager as Standalone Deploy Target

## Context

PRD-001@0.3.0 §5 R15 specifies a one-pager web page with a "Get Proxy" button that redirects to the standalone bot. The original design considered placing it on the exit server (as the mask_host page) or the management server. The PO decided (decision fork #3) that the one-pager should be deployable on any server independently.

## Decision

We will create `deploy-landing.sh` — a fifth independent deploy script that installs the one-pager on any server:
- Installs Angie (or nginx) via Docker.
- Copies a static `index.html` (responsive, dark theme, "Получить прокси" button).
- Prompts for: bot URL (t.me/botname), domain (optional for HTTPS via Let's Encrypt).
- Produces: `infra/landing/docker-compose.yml` + `infra/landing/html/index.html` + Angie config.

The one-pager is purely static — no JavaScript, no backend, no database. Just an HTML page with a link.

The exit server's Angie mask_host is a SEPARATE concern — it serves a generic stub page for DPI camouflage. The one-pager and mask_host are intentionally decoupled.

## Consequences

- **Positive:** Maximum flexibility — operator can put the landing page on a CDN, a shared hosting, or any VPS.
- **Positive:** The exit server's mask_host page is not tied to a specific design — operator can use any web page for DPI masking.
- **Negative / cost:** Fifth deploy script to maintain. Very small scope though (static file + Angie config).
- **Follow-ups:** The mask_host page on the exit server (deployed by `deploy-exit.sh`) is a separate generic stub HTML — not the one-pager.

## Alternatives considered

- **One-pager on exit server (as mask_host)** — original architect recommendation, rejected by PO. Coupling landing page to proxy infrastructure limits deployment flexibility.
- **One-pager on management server** — considered but PO preferred full independence.
