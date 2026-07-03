---
id: RV-ARCH-004
type: arch_review
target_arch: ARCH-001@0.2.0
prd_ref: PRD-001@0.3.0
status: done
created: 2026-07-03
---

# RV-ARCH-004: review of ARCH-001@0.2.0 against PRD-001@0.3.0

**Verdict:** fail
**Summary:** The 0.2.0 TSPU-evasion changes are technically sound and well-justified by research, but the ArchSpec itself has one High documentation gap (§0 Recon Report omits the two knowledge documents that drive the new design) plus three Medium internal-consistency/sequencing gaps that must be fixed before approval.

## Goal coverage

| PRD Goal | Component(s) | Covered? |
|---|---|---|
| G1 — User obtains proxy link via bot | C1 (telemt_proxy package), C2 (standalone bot) | yes |
| G2 — Operator deploys double-hop proxy | C5 (deploy scripts), C7 (Xray Exit Relay) | yes |
| G3 — Operator creates/tracks labelled links | C3 (admin API), C4 (admin panel) | yes |
| G4 — Links survive migration | C5 (migrate.sh), C1 (domain-based links) | yes |
| G5 — Operator monitors from Grafana | C5 (deploy-monitoring.sh), C4 (Grafana embed/link) | yes |
| G6 — Bot embeds in existing bots via pip | C1 (telemt_proxy package) | yes |
| G7 — Users see promoted channel via ad_tag | C5 (deploy-exit.sh configures ad_tag) | yes |

## Checks

- [ ] Every PRD goal covered by ≥1 component.
- [x] No component/ADR violates a PRD Non-Goal.
- [ ] §0 Recon Report present and grounded in docs/knowledge/.
- [x] Every non-trivial decision has a justified ADR; no ADR conflicts.
- [ ] Internally consistent (interfaces agree across sections).
- [x] All references version-pinned and resolve (validate_docs.py clean).
- [ ] Tickets trace to components; depends_on DAG acyclic; parallel tickets' outputs disjoint.
- [x] Each goal has an observable acceptance signal in some ticket §6.

## Findings

### High

- **H1 — §0 Recon Report omits the two knowledge documents that justify 0.2.0.**
  ARCH-001@0.2.0 §0 Recon Report claims "All files in `docs/knowledge/` read and evaluated," but it lists only four documents (`TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md`, `TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md`, `TELEMT_FAKETLS_DOMAIN_SELECTION_REPORT.md`, `TELEMT_GITHUB_ECOSYSTEM_CATALOG.md`). It does **not** list `TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md` or `TELEMT_TSPU_EVASION_PATTERNS.md`, even though every new ADR (ADR-008@0.2.0, ADR-009@0.2.0, ADR-010@0.2.0) and every new ticket (TKT-014@0.2.0–TKT-019@0.2.0) is grounded in those two documents. Per the review mandate, a Recon Report that does not reflect the full knowledge base is a High finding.

### Medium

- **M1 — §1 Overview still says "six components" after C7 was added.**
  ARCH-001@0.2.0 §1 states the architecture consists of "six components" and enumerates only C1–C6. C7 (Xray Exit Relay) is introduced in §3 but never acknowledged in §1. This is an internal inconsistency that should be fixed by updating the overview to "seven components" and adding C7 to the list.

- **M2 — §6 dependency graph / sequencing does not include TKT-014@0.2.0–TKT-019@0.2.0.**
  ARCH-001@0.2.0 §6 contains the original Waves 1–5 graph for TKT-001@0.1.1–TKT-013@0.1.1 only. The six new tickets (TKT-014@0.2.0–TKT-019@0.2.0) and their wave assignments are absent from the ArchSpec itself (they appear only in the draft evaluation document). The sequencing chart in §6 must be updated to show the new Wave 6 and its dependencies.

- **M3 — TKT-017@0.2.0 and TKT-018@0.2.0 can run in parallel but share `deploy-entry.sh`.**
  `TKT-017@0.2.0` depends on `TKT-014@0.2.0`; `TKT-018@0.2.0` depends on `TKT-015@0.2.0`. Once TKT-014@0.2.0 and TKT-015@0.2.0 are done, TKT-017@0.2.0 and TKT-018@0.2.0 have no dependency between them and can execute concurrently. However, both tickets list `infra/entry/deploy-entry.sh` in their §5 Outputs (banner text vs. exit-connectivity prompts). Parallel execution with overlapping output files violates the orchestrator's disjoint-outputs rule. Fix: either add `TKT-017@0.2.0 -> TKT-018@0.2.0` or merge the banner work into TKT-014@0.2.0.

### Low

- **L1 — ADR-008@0.2.0, ADR-009@0.2.0, ADR-010@0.2.0 remain `status: proposed` in the review package.**
  While acceptable during the review phase, the ADRs should be flipped to `accepted` before the ArchSpec is approved. This is a procedural Low, not a technical one.

- **L2 — Encrypted-S2 flow diagram is absent from the ArchSpec.**
  A visual diagram showing client → entry Xray → exit Xray → telemt :8443 would aid reviewers and executors. The draft evaluation document provides the architecture, but the ArchSpec itself only describes C7 textually.

## Top 3 risks (for the PO's 1-line notice)

1. **TKT-018@0.2.0 (encrypted S2) is a large, cross-cutting infra change** — it adds an Xray container on the exit server, switches exit services to host-network mode, and changes telemt's listening port. Any bug here could break proxy connectivity entirely.
2. **Self-steal domain (TKT-019@0.2.0) introduces external DNS/certificate dependencies** — operators must set up an A-record and complete Let's Encrypt validation; failure modes are outside the deploy script's control.
3. **Parallel-ticket output overlap (M3)** — if TKT-017@0.2.0 and TKT-018@0.2.0 execute concurrently, they may conflict on `deploy-entry.sh`, requiring manual merge resolution or a re-run.

## Answers to specific audit questions

- **C7 (Xray Exit Relay) justified?** Yes. It traces to PRD-001@0.3.0 G2 (deploy double-hop proxy) and does not violate the "multi-server clustering" Non-Goal because it is an additional process on the same single exit server.
- **ADR-009@0.2.0 justified by research?** Yes. TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5–§6 and TELEMT_TSPU_EVASION_PATTERNS.md Pattern 3 provide direct evidence of post-handshake payload analysis and production practice of encrypting the RU→EU segment.
- **DAG acyclic and outputs disjoint?** DAG is acyclic. Outputs of independent/parallel tickets are mostly disjoint, but M3 identifies a real overlap between TKT-017@0.2.0 and TKT-018@0.2.0 on `deploy-entry.sh`.
- **Issue #14 (port :8443 → :443) addressed?** Yes. TKT-015@0.2.0 §6 AC2 explicitly requires the entry template outbound `redirect` port to be `:443` instead of `:8443`.
- **always_escalate_on hits?** None. The changes do not introduce new business-impact, cost, regulatory, or irreversible decisions beyond the existing single-exit architecture.
