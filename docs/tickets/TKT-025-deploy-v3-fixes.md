---
id: TKT-025
type: ticket
status: in_review
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: M
created: 2026-07-05
---

# TKT-025: Deploy v3 fixes — Prometheus, PostgreSQL caps, Dockerfile.api, telemt API access

## §1 Goal
Fix 6 bugs found during 3rd test deployment (TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md) across monitoring, mgmt, and exit infrastructure.

## §2 In Scope

| # | Issue | Fix |
|---|-------|-----|
| B1 | Prometheus `--alertmanager.url` removed in v2.54.1 | Remove flag from `infra/monitoring/docker-compose.yml` |
| B2 | PostgreSQL `cap_drop: [ALL]` prevents startup | Remove `cap_drop` and `no-new-privileges` from db service in `infra/mgmt/docker-compose.yml` |
| B3 | Dockerfile.api — `telemt_proxy` not installed | Add `PYTHONPATH=/app` to entrypoint or `RUN uv pip install -e .` |
| B4 | telemt `proxy_protocol` resets :9090/:9091 | Document socat workaround in deploy-exit.sh + add optional socat setup |
| B5 | telemt rustls blocked by CDN WAFs | Document self-steal as required (not optional) for tls_emulation |
| B6 | npm build timeout | Document `screen -dmS` workaround in deploy-mgmt.sh comments |

## §3 NOT In Scope
- TSPU MTProto blocking (architectural — research needed, not a code fix)
- Alternative architectures (tproxy, WireGuard)
- EU VPS provider testing

## §4 Inputs
- `docs/knowledge/TELEMT_DEPLOY_EXPERIENCE_2026-07-04.md` §4
- GitHub issues #45-#50

## §5 Outputs
- `infra/monitoring/docker-compose.yml` — B1
- `infra/mgmt/docker-compose.yml` — B2
- `infra/mgmt/Dockerfile.api` — B3
- `infra/exit/deploy-exit.sh` — B4 (socat docs), B5 (self-steal docs)
- `infra/mgmt/deploy-mgmt.sh` — B6 (screen docs)

## §6 Acceptance Criteria
- [ ] AC1 — Prometheus compose has no `--alertmanager.url` flag
- [ ] AC2 — PostgreSQL db service has no `cap_drop` or `no-new-privileges`
- [ ] AC3 — Dockerfile.api produces a container where `import telemt_proxy` works
- [ ] AC4 — deploy-exit.sh documents socat workaround for :9090/:9091 access
- [ ] AC5 — deploy-exit.sh documents self-steal as required for tls_emulation
- [ ] AC6 — deploy-mgmt.sh documents screen workaround for npm build
- [ ] AC7 — `validate_docs.py` passes
- [ ] AC8 — `shellcheck` passes on all modified scripts

## §7 Constraints
- No new dependencies
- INV-DOCKER: hardening preserved where possible (PostgreSQL is exception — documented)

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-05 Mentor: ticket created from 3rd deploy report.
- 2026-07-05 opencode-executor: started; branch tkt/TKT-025-deploy-v3-fixes
- 2026-07-05 opencode-executor: in_review; tests 217 pass (1 skip); lint clean; typecheck clean; shellcheck clean; validate_docs OK
