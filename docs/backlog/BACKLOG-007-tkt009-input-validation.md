---
id: BACKLOG-007
type: backlog
status: open
target_ticket: TKT-009@0.1.1
created: 2026-07-03
---

# BACKLOG-007: deploy-entry.sh input validation missing

**Source:** RV-CODE-009 F-M2

**Issue:** No input validation for EXIT_SERVER_IP, REALITY_SNI, REALITY_PRIVATE_KEY, or REALITY_SHORT_IDS. A malformed SNI containing `|` could corrupt the `sed` substitution.

**Resolution:** Add validation: EXIT_SERVER_IP (valid IPv4), REALITY_SNI (valid domain, no `|` or `&`), REALITY_PRIVATE_KEY (base64url), REALITY_SHORT_IDS (hex). Reject values with sed-special characters.

**Priority:** Medium
