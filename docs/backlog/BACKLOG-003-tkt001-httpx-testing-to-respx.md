---
id: BACKLOG-003
type: backlog
status: open
target_ticket: TKT-001@0.1.1
created: 2026-07-02
---

# BACKLOG-003: httpx[testing] → respx substitution documentation

**Source:** RV-CODE-001 F-M2

**Issue:** TKT-001@0.1.1 §2 In Scope lists `httpx[testing]` as a dev dependency, but httpx 0.28 has no `testing` extra. The executor substituted `respx` instead. This is technically correct but an undocumented deviation from the ticket text.

**Resolution:** Update TKT-001@0.1.1 §2 text to reflect `respx` as the canonical HTTP mock library, or add an ADR note documenting the substitution. The `respx` package is already in `pyproject.toml` dev dependencies and works correctly.

**Priority:** Low
