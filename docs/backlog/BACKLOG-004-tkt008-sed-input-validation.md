---
id: BACKLOG-004
type: backlog
status: done
target_ticket: TKT-008@0.1.1
created: 2026-07-03
---

# BACKLOG-004: deploy-exit.sh input validation for sed substitution

**Source:** RV-CODE-008 F-M1

**Issue:** `deploy-exit.sh:155-161` uses unvalidated user inputs (AD_TAG, TLS_DOMAIN, etc.) in `sed` replacements with `|` delimiter. Special characters like `|` or `&` can break config generation or be injected into generated config.

**Resolution:** Add input validation for AD_TAG (32-char hex), TLS_DOMAIN (valid domain), DOMAIN (valid domain), and MANAGEMENT_IPS/MONITORING_IPS (valid CIDR). Reject values containing `|`, `&`, or `\`.

**Priority:** Medium

## Resolution

Closed as done (TKT-026@0.1.0). sanitize_input() function added to infra/lib/common.sh.
All user-provided values in deploy-exit.sh (DOMAIN, AD_TAG, TLS_DOMAIN,
TELEMT_SECRET, MANAGEMENT_IPS, MONITORING_IPS, EXIT_REALITY_*, EXIT_VLESS_UUID)
are now sanitized before use in sed substitutions.
