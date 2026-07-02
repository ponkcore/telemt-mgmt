---
id: RV-ARCH-001
type: arch_review
target_arch: ARCH-001@0.1.0
prd_ref: PRD-001@0.3.0
status: done
created: 2026-07-02
---

# RV-ARCH-001: review of ARCH-001@0.1.0 against PRD-001@0.3.0

**Verdict:** pass_with_changes
**Summary:** ARCH-001@0.1.0 covers all PRD-001@0.3.0 goals and has no High blockers, but several Medium gaps must be fixed or explicitly backlogged before execution.

## Goal coverage
| PRD Goal | Component(s) | Covered? |
|---|---|---|
| G1 | C1, C2 | yes |
| G2 | C5 | yes |
| G3 | C3, C4 | yes |
| G4 | C5, C1 | yes |
| G5 | C5, C4 | yes |
| G6 | C1 | yes |
| G7 | C5 | yes |

## Checks
- [x] Every PRD goal covered by >=1 component. ARCH-001@0.1.0 §2 maps G1-G7 to C1-C5; C6 additionally supports PRD-001@0.3.0 R15/J2.
- [x] No component/ADR violates a PRD Non-Goal. The design avoids billing, user tiers implementation, user-facing stats, Bedolaga/Remnawave forks, Remnawave node registration, custom clients, full web registration, and clustering/load balancing.
- [x] §0 Recon Report present and grounded in docs/knowledge/. ARCH-001@0.1.0 §0 lists the four substantive knowledge reports and evaluates reuse/fork candidates before selecting build-from-scratch for the management layer.
- [x] Every non-trivial decision has a justified ADR; no ADR conflicts. ADR-001@0.1.0 through ADR-007@0.1.0 each include Context, Decision, Consequences, and Alternatives, with no direct ADR-to-ADR contradiction found.
- [ ] Internally consistent (interfaces agree across sections). Medium inconsistencies exist in deploy script paths, shared helper ownership/dependencies, ADR-004@0.1.0 vs TKT-002@0.1.0 scope, and TKT-011@0.1.0 Grafana version constraints.
- [x] All references version-pinned and resolve (validate_docs.py clean). `python3 scripts/validate_docs.py` returned `validate_docs: OK — 22 document(s) validated, 0 errors.`
- [x] Tickets trace to components; depends_on DAG acyclic; parallel tickets' outputs disjoint. All 13 tickets use `arch_ref: ARCH-001@0.1.0`; the dependency graph is acyclic and same-wave output paths are disjoint, with one Medium dependency-completeness concern noted below.
- [ ] Each goal has an observable acceptance signal in some ticket §6. G1-G6 have observable ticket acceptance signals, but G7's ad_tag behavior is only prompted for in TKT-008@0.1.0 §6 and lacks an explicit acceptance criterion that telemt config applies ad_tag or that promotion is observable.

## Findings
### High
- none
### Medium
- PRD-001@0.3.0 R3 requires returning a `tg://proxy` link plus QR code, but ARCH-001@0.1.0 §3 C1 only describes link delivery and TKT-004@0.1.0 §3 explicitly excludes QR generation; no ticket §6 acceptance criterion covers QR output.
- ARCH-001@0.1.0 §3 C5 lists deploy scripts as `infra/deploy-*.sh`, while TKT-008@0.1.0 through TKT-012@0.1.0 output scripts under `infra/<target>/deploy-*.sh`; the execution paths are inconsistent across the ArchSpec and tickets.
- ADR-003@0.1.0 says all deploy scripts share `infra/lib/common.sh`, but only TKT-008@0.1.0 owns that output and parallel tickets TKT-009@0.1.0 and TKT-012@0.1.0 do not depend on it; this leaves a hidden dependency in the Wave 2 plan.
- ADR-004@0.1.0 includes `If-Match` support for `PATCH /v1/config`, while TKT-002@0.1.0 §3 explicitly excludes `PATCH /v1/config`; this is a scope contradiction between a cited ADR and its implementing ticket.
- PRD-001@0.3.0 G7/R11 and M6 depend on ad_tag being configured and observable, but TKT-008@0.1.0 §6 only checks that `deploy-exit.sh` prompts for ad_tag, not that the generated telemt config applies it or that promotion can be verified.
- PRD-001@0.3.0 R18 requires a documented extension point for user tiers; ARCH-001@0.1.0 §4 describes one, but no ticket §6 acceptance criterion requires the extension boundary/documentation to be implemented or verified.
- TKT-011@0.1.0 §7 specifies `grafana/grafana:11.3.0` while the same line says Grafana 12.4.2+ is required for dashboard #25119 compatibility, making the monitoring implementation constraint internally contradictory.
### Low
- PRD-001@0.3.0 M1 requires a working fresh-server proxy deployment in under 10 minutes, but the deploy tickets verify idempotence/config/shellcheck rather than an end-to-end timed first connection.
- PRD-001@0.3.0 M5 requires existing links to work after migration without user action; TKT-013@0.1.0 §6 checks DNS/health but not a user reconnect through the unchanged link.
- PRD-001@0.3.0 M6 requires channel subscriber growth attributable to ad_tag; no ticket §6 acceptance criterion traces @MTProxybot stats against proxy user count.

## Top 3 risks (for the PO's 1-line notice)
1. QR-code delivery from PRD-001@0.3.0 R3 is absent from the architecture/ticket acceptance surface.
2. ad_tag configuration and measurement are under-specified, weakening PRD-001@0.3.0 G7 and business attribution for M6.
3. Deploy script path/helper inconsistencies could break the planned parallel execution flow.
