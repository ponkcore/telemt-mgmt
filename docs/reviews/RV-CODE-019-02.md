---
id: RV-CODE-019-02
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/21"
ticket_ref: TKT-019@0.2.0
status: in_review
created: 2026-07-04
---

# RV-CODE-019-02: review of TKT-019@0.2.0 Self-Steal Domain Support (PR #21, iteration 2)

## Verdict: pass

## Summary

F-H1 and F-H2 from iteration 1 are both resolved. All 8 ACs met. No new findings.

## Iteration-1 finding status

- **F-H1 (High): RESOLVED** — `deploy-exit.sh` now stores `SELF_STEAL_DNS_VERIFIED` in `.env`. On re-run, when `SELF_STEAL_DNS_VERIFIED == SELF_STEAL_DOMAIN`, the DNS verification prompt is skipped. INV-IDEMPOTENT satisfied.
- **F-H2 (High): RESOLVED** — After certbot acquisition, certs are copied to `./mask/certs/` (fullchain.pem, privkey.pem). `TLS_CERT_PATH` and `TLS_KEY_PATH` are set to `/var/www/mask/certs/fullchain.pem` and `/var/www/mask/certs/privkey.pem`, which are accessible inside the Angie container via the existing `./mask:/var/www/mask:ro` volume mount. The `angie-selsteal.conf.template` comments updated to document these paths.

## AC checklist

- AC1 ✅ — Default `TLS_DOMAIN` = `www.microsoft.com` (`deploy-exit.sh:123`)
- AC2 ✅ — Self-steal detection via `KNOWN_THIRD_PARTY_DOMAINS` array + `SELF_STEAL_DOMAIN` env var (`deploy-exit.sh:82-144`)
- AC3 ✅ — DNS verification prompt before cert acquisition, idempotent on re-run (`deploy-exit.sh:150-185`)
- AC4 ✅ — `angie-selsteal.conf.template` exists with TLS server block on :443 (`:78-97`)
- AC5 ✅ — Self-steal: `mask_host = __MASK_HOST__` → domain, `mask_port = __MASK_PORT__` → 443 (`config.toml.template:68,72` + `deploy-exit.sh:240-241`)
- AC6 ✅ — Third-party: `mask_host` → domain, `mask_port` → 8080 (`deploy-exit.sh:255-256`)
- AC7 ✅ — README documents DNS A-record, Let's Encrypt cert, advantages
- AC8 ✅ — Idempotent: `load_env` + `prompt_for` skip on re-run; `SELF_STEAL_DNS_VERIFIED` skips DNS prompt; cert existence check skips certbot

## Findings

None.

## Checks

- `shellcheck infra/exit/deploy-exit.sh` → OK
- `python3 scripts/validate_docs.py` → OK — 51 document(s), 0 errors
- `nix-shell --run 'uv run pytest -q'` → 198 passed, 1 skipped
- `nix-shell --run 'uv run ruff check telemt_proxy api bot tests'` → All checks passed

## Hand-back

```
rv: RV-CODE-019-02  path: docs/reviews/RV-CODE-019-02.md
verdict: pass
counts: 0 high, 0 medium, 0 low
highs:
  - (none)
recommendation: merge
```
