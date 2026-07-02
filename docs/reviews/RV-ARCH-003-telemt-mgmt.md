---
id: RV-ARCH-003
type: arch_review
target_arch: ARCH-001@0.1.2
prd_ref: PRD-001@0.3.0
status: done
created: 2026-07-02
---

# RV-ARCH-003: final audit of ARCH-001@0.1.2 against PRD-001@0.3.0

**Verdict:** pass
**Summary:** ARCH-001@0.1.2 resolves the `create_router()` interface drift from RV-ARCH-002 and remains fully aligned with PRD-001@0.3.0; no Highs or Mediums, and the only remaining issue is the already-backlogged TKT-005@0.1.0 slowapi contradiction.

## Goal coverage

| PRD Goal | Component(s) | Covered? |
|---|---|---|
| G1 — User obtains proxy link via bot | C1, C2 | yes |
| G2 — Operator deploys double-hop proxy | C5 | yes |
| G3 — Operator creates/tracks labelled links | C3, C4 | yes |
| G4 — Links survive migration | C5 (migrate), C1 (domain links) | yes |
| G5 — Operator monitors from Grafana | C5, C4 | yes |
| G6 — Bot embeds in existing bots via pip | C1 | yes |
| G7 — Users see promoted channel via ad_tag | C5 | yes |

## Checks

- [x] Every PRD goal covered by ≥1 component. ARCH-001@0.1.2 §2 maps G1–G7 to C1–C6.
- [x] No component/ADR violates a PRD Non-Goal. The design excludes paid/billing, user tiers, user-facing stats, Bedolaga/Remnawave forks, Remnawave node registration, custom clients, full web registration, and clustering/load balancing.
- [x] §0 Recon Report present and grounded in `docs/knowledge/`. ARCH-001@0.1.2 §0 lists the four substantive knowledge reports and the build-from-scratch decision.
- [x] Every non-trivial decision has a justified ADR; no ADR conflicts. ADR-001@0.1.2 through ADR-007@0.1.0 each include Context, Decision, Consequences, and Alternatives; the ADR-001@0.1.2 revision aligns with TKT-004@0.1.1. No direct contradiction remains.
- [x] Internally consistent (interfaces agree across sections). The `create_router()` signature now matches across ARCH-001@0.1.2 §3 C1, ADR-001@0.1.2, and TKT-004@0.1.1; the `ProxyConfig` interface is documented; the C2 embed example includes `config` construction; the M3 note is present.
- [x] All references version-pinned and resolve (`validate_docs.py` clean). `python3 scripts/validate_docs.py` returned `validate_docs: OK — 25 document(s) validated, 0 errors.`
- [x] Tickets trace to components; depends_on DAG acyclic; parallel tickets' outputs disjoint. All 13 tickets map to C1–C6; the DAG in ARCH-001@0.1.2 §6 is acyclic; Wave 2–5 output paths are disjoint.
- [x] Each goal has an observable acceptance signal in some ticket §6. G1–G7 acceptance criteria are present across TKT-004@0.1.1, TKT-006@0.1.0, TKT-007@0.1.1, TKT-008@0.1.1, TKT-009@0.1.1, TKT-011@0.1.1, and TKT-013@0.1.1.

## Findings

### High
- none

### Medium
- none

### Low
- **TKT-005@0.1.0 §7 dependency contradiction (backlogged).** The ticket states “No new dependencies beyond TKT-001@0.1.1” but then suggests “use `slowapi` or custom middleware (add `slowapi` to dev deps if needed).” Adding `slowapi` would be a new dependency. This is correctly tracked as BACKLOG-001 (status: open) and does not block the architecture; the recommended resolution is Option B (custom middleware). The executor should not add `slowapi` without first updating TKT-001@0.1.1 / TKT-005@0.1.0.

## Resolution verification

The RV-ARCH-002 Medium is resolved in ARCH-001@0.1.2 / ADR-001@0.1.2.

| Finding | Status |
|---|---|
| `create_router()` signature mismatch between ARCH-001@0.1.2 / ADR-001@0.1.2 and TKT-004@0.1.1 | resolved |

**Evidence:**
- ARCH-001@0.1.2 §3 C1 documents `create_router(telemt_client, db_session_factory, config, tier_service=None)`.
- ARCH-001@0.1.2 §3 C1 documents `ProxyConfig` dataclass with `server`, `port`, and `salt` fields.
- ARCH-001@0.1.2 §3 C2 embed example includes `config = ProxyConfig(...)` and passes it to `create_router(...)`.
- ADR-001@0.1.2 Decision section includes the same `config` parameter and the same embed example.
- ADR-001@0.1.2 frontmatter has `version: 0.1.2`.
- ARCH-001@0.1.2 frontmatter `adrs:` list includes `ADR-001@0.1.2`.
- The M3 measurement note is present in both ARCH-001@0.1.2 §3 C2 and ADR-001@0.1.2: the `config` construction is deployment configuration, not integration; core integration stays 3 lines.

## Regressions from the 0.1.2 patch

- No new High, Medium, or Low findings were introduced by the patch.
- `ARCH-001@0.1.2` version is `0.1.2`, `ADR-001@0.1.2` version is `0.1.2`; other ADRs remain at their prior versions; ticket versions are unchanged.
- Cross-references in `ARCH-001@0.1.2` frontmatter match the actual file versions.
- `validate_docs.py` is clean; no bare or dangling references.
- No new internal contradictions were introduced.

## Top 3 risks (for the PO's 1-line notice)

1. **M6 ad_tag attribution remains a manual operator correlation** between @MTProxybot stats and the admin panel; no automated acceptance signal exists, leaving business-impact measurement dependent on operator discipline.
2. **M1/M2 timing targets** are measured by deploy/migration script timing wrappers but not enforced in CI, so real-world performance depends on operator runtime verification.
3. **TKT-005@0.1.0 rate-limiting text remains ambiguous** even though it is backlogged; if an executor misreads it and adds `slowapi`, an unauthorized dependency would be introduced.

## Escalation note

The target architecture touches `autonomy.always_escalate_on` categories inherited from PRD-001@0.3.0: **cost** (extra double-hop entry server) and **regulatory / business impact** (DPI evasion for Russian users, channel promotion via ad_tag). Because `project.jsonc.autonomy.arch_approval` is set to `manual`, the PO will approve the ArchSpec by hand; no separate escalation is required.
