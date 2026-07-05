---
id: RV-CODE-026
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/52"
ticket_ref: TKT-026@0.1.0
status: in_review
created: 2026-07-05
---

# RV-CODE-026: review of TKT-026@0.2.1 — Backlog cleanup / deploy hardening + Low findings (PR #52)

**Verdict:** `pass_with_changes`
**Summary:** All ACs are verifiably met and project checks are green, but one Medium residual-injection finding in `sanitize_input()` should be fixed or backlogged before the next deploy-script ticket.

## Contract compliance

- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10 + TKT-025@0.2.1 §10 version-pin fix, which is explicitly allowed orchestrator work).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [x] `project.jsonc` checks green (typecheck/lint/test/validate_docs).
- [x] All `project.jsonc` invariants hold in changed code.

## Acceptance criteria

- **AC1** — `infra/lib/common.sh:126` defines `sanitize_input()` and strips `'`, `"`, `` ` ``, `;`.
- **AC2** — `infra/exit/deploy-exit.sh` sanitizes `DOMAIN`, `AD_TAG`, `TLS_DOMAIN`, `TELEMT_SECRET`, `MANAGEMENT_IPS`, `MONITORING_IPS`, `EXIT_REALITY_*`, `EXIT_VLESS_UUID`. `infra/entry/deploy-entry.sh` sanitizes `EXIT_SERVER_IP`, `EXIT_VLESS_UUID`, `EXIT_PUBLIC_KEY`, `EXIT_REALITY_SNI`, `EXIT_SHORT_ID`.
- **AC3** — `infra/exit/deploy-exit.sh:591-623` wraps every UFW command in `if ! sudo ufw ...; then echo "WARNING: UFW rule failed..." >&2; fi`.
- **AC4** — `infra/exit/deploy-exit.sh:646-661` defines `_deploy_rollback()` and sets `trap _deploy_rollback ERR` immediately before `docker compose up -d`, removing it with `trap - ERR` after success.
- **AC5** — `telemt_proxy/qr.py:47` uses `img.save(buffer, format="PNG")`.
- **AC6** — `infra/entry/docker-compose.yml:4,13` comment now says PROXYv1; `:35-38` adds `ulimits: nofile: {soft: 65536, hard: 262144}`.
- **AC7** — `api/routes/links.py:119-127` adds the required explanatory comment for the `hash_telegram_id()` divergence.
- **AC8** — `README.md:110-126` adds the "Landing page deployment" section.
- **AC9** — `tests/test_deploy_scripts.py:73-84` runs `shellcheck -x` on all 5 deploy scripts; `:33-51` tests `sanitize_input()` behaviour.
- **AC10** — All 7 backlog files updated: BACKLOG-001/008 `status: wontfix`; BACKLOG-003/004/005/006/007 `status: done`.
- **AC11** — `python3 scripts/validate_docs.py` passes: 68 documents, 0 errors.
- **AC12** — `nix-shell --run 'uv run pytest -q'` passes: 253 pass, 1 skip.

## Findings

### High (block merge)
- None.

### Medium (fix or backlog)
- **F-M1: `sanitize_input()` does not strip sed-special / shell-expansion characters** — `infra/lib/common.sh:126-129`
  The function strips only `'`, `"`, `` ` ``, and `;` as required by the ticket, but the generated configs are produced by `sed` using `|` as the delimiter and the values are later expanded inside bash double quotes. A value containing `|`, `&`, `\`, or `$` can still break the `sed` substitution (`|` splits the pattern, `&` is replaced by the matched text in the RHS, `\` can escape the delimiter, and `$` enables command substitution like `$(...)` when the variable is expanded inside the double-quoted `sed` command). This leaves a residual injection/breakage vector despite meeting the literal AC. Recommended fix: extend `sanitize_input()` to also remove `|`, `&`, `\`, `$` (and arguably `(`, `)`, `<`, `>`), or switch template generation to a non-sed-based method (e.g. envsubst with a whitelist).

### Low (optional)
- **F-L1: Pre-existing shellcheck warning in `common.sh`** — `infra/lib/common.sh:80`
  Shellcheck reports `SC2163` on `export "$var_name"` in `prompt_for()`. This is pre-existing (not introduced by this PR) and is a false-positive for dynamic variable names. Consider adding `# shellcheck disable=SC2163` to silence it so future reviews do not have to re-triage.
- **F-L2: Unused test helpers in `tests/test_deploy_scripts.py`** — `tests/test_deploy_scripts.py:39,50`
  `ALL_SHELL_SCRIPTS` and `_source_common_sh()` are defined but never used. They can be removed or wired into a future test that also shellchecks `common.sh` and `scripts/migrate.sh`.
- **F-L3: `deploy-entry.sh` still swallows UFW failures** — `infra/entry/deploy-entry.sh` (out of scope)
  The entry script's UFW commands still use `|| true` / `&>/dev/null`. This is not part of the ticket scope (BACKLOG-005 explicitly targeted `deploy-exit.sh`), but the AC3 wording "deploy scripts" could be read broadly. No merge blocker, but consider a follow-up ticket for consistency.

## Red-team probes

- **error_paths:** The rollback trap covers the `docker compose up -d` path. Pre-up failures (certbot, DNS abort, missing templates) exit before the trap is set, so there is no partially-started state to roll back — acceptable. `sanitize_input()` returns empty for empty input, but `prompt_for()` already rejects empty interactive values.
- **concurrency:** No shared mutable state or parallel execution in the changed deploy scripts; no race conditions introduced.
- **input_validation:** `sanitize_input()` meets the literal ticket contract but is incomplete: it does not strip `|`, `&`, `\`, `$`, which can still break sed substitutions or trigger shell expansion in the double-quoted `sed` commands (see F-M1).
- **authz_isolation:** No privilege-escalation changes. UFW rules still run under `sudo`, which is necessary for firewall management; the script already assumes root-like deploy privileges.
- **secrets:** No hardcoded secrets in new code or tests. Secrets continue to flow through `.env` only (`project.jsonc` INV-SECRETS).
- **observability:** UFW failures now emit descriptive `WARNING: UFW rule failed: ...` messages to stderr, including the rule that failed.
- **rollback:** `infra/exit/deploy-exit.sh:646-661` sets `trap _deploy_rollback ERR` after config generation and before `docker compose up -d`, calling `docker compose down` (or `docker-compose down`) on failure. The trap is removed with `trap - ERR` after successful deploy. Correct placement and behaviour.
- **dns_failover:** N/A for this diff. Self-steal DNS verification prompt requires manual operator confirmation; no automated DNS failover logic changed.

## Check evidence

```text
python3 scripts/validate_docs.py          → OK — 68 document(s) validated, 0 errors.
nix-shell --run 'uv run pytest -q'        → 253 passed, 1 skipped
nix-shell --run 'uv run mypy --strict ...' → Success: no issues found in 25 source files
nix-shell --run 'uv run ruff check ...'    → All checks passed!
shellcheck -x infra/exit/deploy-exit.sh infra/entry/deploy-entry.sh infra/lib/common.sh
  → SC2163 warning on pre-existing line 80 of common.sh (F-L1)
```
