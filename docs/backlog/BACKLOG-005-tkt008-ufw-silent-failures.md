---
id: BACKLOG-005
type: backlog
status: done
target_ticket: TKT-008@0.1.1
created: 2026-07-03
---

# BACKLOG-005: deploy-exit.sh UFW failures silently swallowed

**Source:** RV-CODE-008 F-M2

**Issue:** `deploy-exit.sh:191-206` firewall rules swallow UFW/sudo failures with `|| true`. Invalid IPs or permission issues are silently ignored, leaving ports potentially unprotected.

**Resolution:** Remove `|| true` from UFW rules; use proper error handling that logs failures and aborts if critical firewall rules cannot be applied. Keep `|| true` only for idempotent "rule already exists" cases.

**Priority:** Medium

## Resolution

Closed as done (TKT-026@0.1.0). All UFW commands in deploy-exit.sh now use
`if ! ufw ...; then echo "WARNING: UFW rule failed" >&2; fi` instead of
`|| true`. Failures are reported to stderr instead of being silently swallowed.
