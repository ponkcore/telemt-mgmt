---
id: TKT-026
type: ticket
status: done
arch_ref: ARCH-001@0.2.1
depends_on: []
estimate: M
created: 2026-07-05
---

# TKT-026: Backlog cleanup — deploy script hardening + code review Low findings

## §1 Goal
Close all 7 open backlog items in one pass: deploy script input validation, UFW error reporting, rollback on failed compose, and 7 code review Low findings.

## §2 In Scope

### Deploy script hardening (BACKLOG-004, 005, 006, 007)

| # | What | Fix |
|---|------|-----|
| 004 | deploy-exit.sh: no sed input validation | Add `sanitize_input()` to `infra/lib/common.sh` — strip single quotes, double quotes, backticks, semicolons from user input |
| 005 | deploy-exit.sh: UFW failures silently swallowed | Wrap UFW commands in `if ! ufw ...; then echo "WARNING: UFW rule failed" >&2; fi` |
| 006 | deploy-exit.sh: no rollback on failed docker compose up | Add `trap 'docker compose down' ERR` after config generation, before `docker compose up -d` |
| 007 | deploy-entry.sh: no input validation | Use same `sanitize_input()` from common.sh |

### Code review Low findings (BACKLOG-003, items L1-L7)

| # | What | Fix |
|---|------|-----|
| L1 | qr.py uses `kind=` instead of `format=` | Change `kind="PNG"` to `format="PNG"` in `telemt_proxy/qr.py` |
| L2 | Entry docker-compose comment says PROXYv2 | Update comment to "PROXYv1" in `infra/entry/docker-compose.yml` |
| L3 | JWT in localStorage | Document as accepted risk in ADR-002@0.1.0.1.0 — no code change |
| L4 | No integration tests for deploy scripts | Add `tests/test_deploy_scripts.py` — smoke test that runs `shellcheck` on all deploy scripts and validates config generation with mock .env |
| L5 | Admin links bypass hash_telegram_id | Add code comment in `api/routes/links.py` explaining intentional divergence |
| L6 | Entry docker-compose missing ulimits | Add `ulimits: nofile: soft: 65536, hard: 262144` to entry compose |
| L7 | README could mention landing deploy | Add landing page section to README.md |

### BACKLOG-001 (slowapi wording)

| What | Fix |
|------|-----|
| TKT-005@0.1.0.1.0 §7 says "No new dependencies" but mentions slowapi | This is ticket content — Mentor cannot edit tickets. Close BACKLOG-001 as wontfix (executor already chose custom middleware, no slowapi used) |

## §3 NOT In Scope
- BACKLOG-008 (tls_emulation fetch fail) — non-blocking, project conserved, close as wontfix
- BACKLOG-002 (environment awareness) — already done
- Any architecture changes
- TSPU JA4 blocking (addressed in ADR-011@0.2.1.2.1, not a code fix)

## §4 Inputs
- `docs/backlog/BACKLOG-001-tkt005-slowapi-contradiction.md`
- `docs/backlog/BACKLOG-003-code-review-low-findings.md`
- `docs/backlog/BACKLOG-004-tkt008-sed-input-validation.md`
- `docs/backlog/BACKLOG-005-tkt008-ufw-silent-failures.md`
- `docs/backlog/BACKLOG-006-tkt008-no-rollback.md`
- `docs/backlog/BACKLOG-007-tkt009-input-validation.md`
- `docs/reviews/RV-CODE-FULL-telemt-mgmt.md` — L1-L7

## §5 Outputs
- `infra/lib/common.sh` — sanitize_input() function
- `infra/exit/deploy-exit.sh` — input validation, UFW error handling, rollback trap
- `infra/entry/deploy-entry.sh` — input validation
- `telemt_proxy/qr.py` — L1 (format= instead of kind=)
- `infra/entry/docker-compose.yml` — L2 (comment), L6 (ulimits)
- `api/routes/links.py` — L5 (code comment)
- `README.md` — L7 (landing deploy section)
- `tests/test_deploy_scripts.py` — L4 (smoke tests)
- `docs/backlog/BACKLOG-001-tkt005-slowapi-contradiction.md` — close as wontfix
- `docs/backlog/BACKLOG-003-code-review-low-findings.md` — close as done
- `docs/backlog/BACKLOG-004-tkt008-sed-input-validation.md` — close as done
- `docs/backlog/BACKLOG-005-tkt008-ufw-silent-failures.md` — close as done
- `docs/backlog/BACKLOG-006-tkt008-no-rollback.md` — close as done
- `docs/backlog/BACKLOG-007-tkt009-input-validation.md` — close as done
- `docs/backlog/BACKLOG-008-tls-emulation-fetch-fail.md` — close as wontfix

## §6 Acceptance Criteria
- [ ] AC1 — `infra/lib/common.sh` has `sanitize_input()` function that strips dangerous chars
- [ ] AC2 — `deploy-exit.sh` and `deploy-entry.sh` use `sanitize_input()` on all user-provided values
- [ ] AC3 — UFW commands in deploy scripts report failures (not silently swallow)
- [ ] AC4 — `deploy-exit.sh` has `trap` for rollback on failed `docker compose up`
- [ ] AC5 — `qr.py` uses `format="PNG"` (not `kind="PNG"`)
- [ ] AC6 — Entry docker-compose comment says "PROXYv1", has ulimits
- [ ] AC7 — `api/routes/links.py` has comment explaining admin link hashing divergence
- [ ] AC8 — README.md has landing deploy section
- [ ] AC9 — `tests/test_deploy_scripts.py` exists, runs shellcheck on all deploy scripts
- [ ] AC10 — All 7 backlog files updated to `status: done` or `status: wontfix`
- [ ] AC11 — `validate_docs.py` passes
- [ ] AC12 — All existing tests still pass

## §7 Constraints
- No new dependencies
- `sanitize_input()` must not break legitimate domain names, IPs, or labels with hyphens/dots

## §8 Definition of Done
- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log
- 2026-07-05 Mentor: ticket created (backlog cleanup + hardening, final pre-conservation pass)
- 2026-07-05 opencode-executor: started
- 2026-07-05 opencode-executor: in_review; tests 253 pass (1 skip); lint clean; typecheck clean; shellcheck clean
- 2026-07-05 opencode-executor: PR #52 opened, branch tkt/TKT-026-backlog-cleanup-hardening
- 2026-07-05 opencode-orchestrator: merged in 120b2a0; RV-CODE-026 verdict=pass_with_changes (F-M1+F-L2 fixed, F-L3 backlogged — deploy-entry.sh UFW out of scope)
