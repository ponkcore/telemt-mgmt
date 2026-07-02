---
id: RV-CODE-009
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/6"
ticket_ref: TKT-009@0.1.1
status: in_review
created: 2026-07-03
---

# RV-CODE-009: review of TKT-009 — Deploy Script: Entry Server (PR #6)

**Verdict:** pass_with_changes
**Summary:** The PR meets all seven ACs and respects scope, but the generated Xray `shortIds` array is malformed and user inputs are not validated, which should be fixed or backlog-tracked before considering production-ready.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
  - Changed: `infra/entry/deploy-entry.sh`, `infra/entry/docker-compose.yml`, `infra/entry/xray-config.json.template`, `infra/entry/.env.example`.
  - Also: `docs/tickets/TKT-009-deploy-entry.md` status `ready` → `in_review` and §10 log append — allowed.
- [x] No §3 NOT-In-Scope term touched.
  - Exit server, AmneziaWG/VPS_DOUBLE_HOP, and multiple entry servers are untouched.
- [x] No unauthorised runtime dependency.
  - Uses only `ghcr.io/xtls/xray-core:latest` (per §7 Constraints) and existing `infra/lib/common.sh`.
- [x] Every §6 AC verifiably met (citations below).
- [ ] project.jsonc checks green (typecheck/lint/test).
  - `mypy --strict telemt_proxy api bot`: PASS.
  - `ruff check telemt_proxy api bot tests`: PASS.
  - `npx tsc --noEmit` (frontend): PASS.
  - `uv run pytest -q`: FAIL — pre-existing environment issue (`libstdc++.so.6: cannot open shared object file` / greenlet import failure in `tests/test_models.py`). Not caused by this PR (no Python code changed). Noted as Low.
- [x] All project.jsonc invariants hold.
  - INV-DOCKER satisfied (`cap_drop: [ALL]`, `read_only: true`, `security_opt: [no-new-privileges:true]`, `cap_add: [NET_BIND_SERVICE]`).
  - INV-IDEMPOTENT satisfied (`.env` load + re-run detection via `load_env`/`prompt_for`).
  - INV-SECRETS satisfied (secrets in `.env`, `.env.example` documents names, `.env` gitignored).

## Acceptance criteria
- AC1 — `deploy-entry.sh:59-61` loads existing `.env` via `load_env`; `common.sh:32-38` sources the file; `common.sh:54-59` returns existing values without prompting — idempotent re-run is supported.
- AC2 — `deploy-entry.sh:66-73` prompts for `EXIT_SERVER_IP` and `REALITY_SNI`; `deploy-entry.sh:77-141` prompts for / auto-generates `REALITY_PRIVATE_KEY` and `REALITY_SHORT_IDS`.
- AC3 — `xray-config.json.template:39` sets `"fingerprint": "firefox"` (not chrome).
- AC4 — `xray-config.json.template:58-59` sets `"redirect": "__EXIT_SERVER_IP__:8443"` and `"proxyProtocol": 2` for PROXYv2 real-client-IP preservation.
- AC5 — `docker-compose.yml:21-27` includes `cap_drop: ALL`, `cap_add: NET_BIND_SERVICE`, `read_only: true`, `security_opt: no-new-privileges:true`.
- AC6 — `shellcheck infra/entry/deploy-entry.sh` exits 0 with no warnings/errors.
- AC7 — `deploy-entry.sh:24-35` defines `DEPLOY_START_TIME`, `finish()` trap, and prints `"Total elapsed time: ${mins}m ${secs}s"` on exit.

## Findings
### High (block merge)
- <none>

### Medium (fix or backlog)
- **F-M1: `xray-config.json.template:38` — `shortIds` array is malformed.**
  The template is `"shortIds": ["__REALITY_SHORT_IDS__"]` and the script (`deploy-entry.sh:126-129`) sets `REALITY_SHORT_IDS="id1,id2"`. The resulting JSON is `["id1,id2"]` — a single string element containing a comma, instead of two separate short IDs (`["id1", "id2"]`). This may cause Xray to reject the short ID or break client handshakes. Fix: either make the template `"shortIds": [__REALITY_SHORT_IDS__]` and have the script emit quoted comma-separated values, or generate a proper JSON array in the script and template it as `"shortIds": __REALITY_SHORT_IDS__`.
- **F-M2: No input validation for operator-provided values.**
  `EXIT_SERVER_IP`, `REALITY_SNI`, `REALITY_PRIVATE_KEY`, and `REALITY_SHORT_IDS` are accepted verbatim. A malformed IP/domain or an SNI containing the `|` sed delimiter could corrupt the generated config or the `.env` file. Add minimal validation/sanitization (e.g., IP/FQDN regex for exit server, domain check for SNI, base64/hex regex for keys/IDs).

### Low (optional)
- **F-L1: UFW commands silently swallow failures.**
  `deploy-entry.sh:164-165,169` redirect stdout/stderr to `/dev/null` and `|| true` all UFW calls. A permission or state failure will not be reported. Consider surfacing non-fatal warnings or failing explicitly when UFW is present but cannot be configured.
- **F-L2: Pre-existing pytest environment failure.**
  `uv run pytest -q` fails with `libstdc++.so.6: cannot open shared object file` during `tests/test_models.py` setup. This is unrelated to the PR but blocks the project.jsonc `test` command in this environment. Escalate to Mentor/PO to fix the CI runner or lock greenlet version.

## Red-team probes (one line each; N/A allowed)
- error_paths: `xray x25519` or `docker run` key generation failure is caught by `set -e`, but empty/malformed key output from `grep`/`awk` is not validated before saving (F-M2).
- concurrency: N/A — single-threaded bash deploy script.
- input_validation: No validation of `EXIT_SERVER_IP`, `REALITY_SNI`, keys, or short IDs; SNI containing `|` would break the `sed` substitution (F-M2).
- prompt_injection: N/A — no LLM prompts.
- authz_isolation: N/A — deploy script runs interactively as root; isolation is at the host/container level (INV-DOCKER satisfied).
- secrets: Satisfied — `REALITY_PRIVATE_KEY` stored in `.env` (gitignored), only first 8 chars printed; `.env.example` documents all secret names.
- observability: Satisfied — `finish()` timing wrapper (AC7) and Docker json-file logging with rotation configured.
- rollback: No rollback implemented; not required by this ticket.
- dns_failover: N/A — single exit-server target; failover is out of scope for TKT-009.
