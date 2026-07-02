---
id: RV-ARCH-002
type: arch_review
target_arch: ARCH-001@0.1.2
prd_ref: PRD-001@0.3.0
status: done
created: 2026-07-02
---

# RV-ARCH-001-v2: re-audit of ARCH-001@0.1.1 against PRD-001@0.3.0

**Verdict:** pass_with_changes
**Summary:** ARCH-001@0.1.1 resolves all 10 findings from RV-ARCH-001 and remains aligned with PRD-001@0.3.0; one new Medium interface inconsistency introduced by the patch requires architect correction before execution.

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
- [x] Every PRD goal covered by ≥1 component. ARCH-001@0.1.1 §2 maps G1–G7 to C1–C6; C6 additionally supports PRD-001@0.3.0 R15.
- [x] No component/ADR violates a PRD Non-Goal. The design avoids paid/billing, user-tier implementation, user-facing stats, Bedolaga/Remnawave forks, Remnawave node registration, custom clients, full web registration, and clustering/load balancing.
- [x] §0 Recon Report present and grounded in `docs/knowledge/`. ARCH-001@0.1.1 §0 lists the four substantive knowledge reports and the build-from-scratch decision.
- [x] Every non-trivial decision has a justified ADR; no ADR conflicts. ADR-001@0.1.0 through ADR-007@0.1.0 each include Context, Decision, Consequences, and Alternatives; ADR-003@0.1.1 and ADR-004@0.1.1 carry revision notes. No direct contradiction remains.
- [ ] Internally consistent (interfaces agree across sections). One interface contract drift: the `create_router()` signature in ARCH-001@0.1.1 §3 C1 / ADR-001@0.1.0 does not match the `config` parameter added in TKT-004@0.1.1 (see Medium finding).
- [x] All references version-pinned and resolve (`validate_docs.py` clean). `python3 scripts/validate_docs.py` returned `validate_docs: OK — 23 document(s) validated, 0 errors.`
- [x] Tickets trace to components; depends_on DAG acyclic; parallel tickets' outputs disjoint. All 13 tickets use `arch_ref: ARCH-001@0.1.1`; the DAG is acyclic after moving `common.sh` to TKT-001@0.1.1; Wave 2–5 output paths are disjoint.
- [x] Each goal has an observable acceptance signal in some ticket §6. G1–G7 acceptance criteria are now present across TKT-004@0.1.1, TKT-006@0.1.0, TKT-007@0.1.1, TKT-008@0.1.1, TKT-009@0.1.1, TKT-011@0.1.1, and TKT-013@0.1.1.

## Findings
### High
- none

### Medium
- **ARCH-001@0.1.1 §3 C1 / ADR-001@0.1.0 / TKT-004@0.1.1 interface mismatch.** ARCH-001@0.1.1 §3 C1 documents `create_router(telemt_client, db_session_factory, tier_service=None)`; ADR-001@0.1.0 documents `create_router(telemt_client, db_session_factory)`. TKT-004@0.1.1 implements and tests `create_router(telemt_client, db_session_factory, config, tier_service=None)` and outputs `telemt_proxy/config.py`. The 3-line embed example in ARCH-001@0.1.1 §3 C2 and ADR-001@0.1.0 also omits `config`. Because the router needs `server`, `port`, and `salt` to build proxy links and QR codes, the documented contract is incomplete and contradicts the implementing ticket. This is a regression introduced by the 0.1.1 patch (the `config` parameter does not appear in the ArchSpec contract).

### Low
- **TKT-005@0.1.0 §7 dependency contradiction.** The ticket states “No new dependencies beyond TKT-001@0.1.1” but then suggests “use `slowapi` or custom middleware (add `slowapi` to dev deps if needed).” Adding `slowapi` would be a new dependency; the ticket should either authorize it in §7 or remove the `slowapi` option.

## Top 3 risks (for the PO's 1-line notice)
1. **`create_router()` interface drift** could break the documented 3-line embed contract (G1/G6) if the executor follows the ArchSpec/ADR example rather than TKT-004@0.1.1.
2. **M6 ad_tag attribution remains a manual correlation** between @MTProxybot stats and the admin panel; no automated acceptance signal exists, leaving business-impact measurement dependent on operator discipline.
3. **M1/M2 timing/reconnect metrics** are measured by deploy/migration scripts but not enforced in CI, so real-world performance depends on operator runtime verification.

## Resolution verification
All 10 findings from RV-ARCH-001 are resolved in ARCH-001@0.1.1 / associated tickets.

| Finding | Status | Evidence |
|---|---|---|
| **M1** QR code | resolved | TKT-001@0.1.1 §2 adds `qrcode[pil]` and `Pillow` to dependencies; TKT-004@0.1.1 §5 outputs `telemt_proxy/qr.py`, §6 AC10 requires QR PNG generation, and §3 no longer excludes QR; ARCH-001@0.1.1 §3 C1 explicitly describes QR generation. |
| **M2** deploy paths | resolved | ARCH-001@0.1.1 §3 C5 now lists `infra/entry/deploy-entry.sh`, `infra/exit/deploy-exit.sh`, `infra/mgmt/deploy-mgmt.sh`, `infra/monitoring/deploy-monitoring.sh`, and `infra/landing/deploy-landing.sh`, matching the ticket outputs. |
| **M3** common.sh | resolved | TKT-001@0.1.1 §5 owns `infra/lib/common.sh`; TKT-008@0.1.1 §5 no longer owns it; ADR-003@0.1.1 revision note states `common.sh` is created in TKT-001@0.1.1 to preserve Wave 2 parallelism. |
| **M4** ADR-004@0.1.1 PATCH / If-Match | resolved | ADR-004@0.1.1 no longer mentions `If-Match` or `PATCH /v1/config`; revision note confirms removal per RV-ARCH-001; TKT-002@0.1.0 §3 explicitly excludes `PATCH /v1/config`. |
| **M5** ad_tag config | resolved | TKT-008@0.1.1 §6 AC9 requires `ad_tag` in `config.toml`, AC10 requires `use_middle_proxy = true`, AC11 requires the @MTProxybot `/myproxies` post-deploy message; ARCH-001@0.1.1 §3 C5 deploy-exit description includes ad_tag generation and the promotion verification prompt. |
| **M6** R18 extension point | resolved | TKT-004@0.1.1 §2 documents the `tier_service=None` parameter as the R18 extension point; §6 AC11 requires the parameter and its documentation. |
| **M7** Grafana version | resolved | TKT-011@0.1.1 §7 specifies `grafana/grafana:12.4.2` and explicitly notes Grafana 12.4.2+ is required for dashboard #25119 compatibility. |
| **L1** timed deploy | resolved | TKT-008@0.1.1 §6 AC12 and TKT-009@0.1.1 §6 AC7 both require timing wrappers that print elapsed time for M1 measurement. |
| **L2** migration reconnect | resolved | TKT-013@0.1.1 §6 AC9 adds a post-migration verification command and confirms the link FQDN is unchanged (INV-DOMAIN). |
| **L3** M6 attribution | resolved | TKT-007@0.1.1 §6 AC10 requires a Dashboard link/card to @MTProxybot promotion stats; ARCH-001@0.1.1 §8 Observability now contains the “M6 Attribution — ad_tag Promotion Tracking” subsection. |

## New issues introduced by the 0.1.1 patch
- `create_router()` signature mismatch between ARCH-001@0.1.1 / ADR-001@0.1.0 and TKT-004@0.1.1 (Medium, documented above).
- TKT-005@0.1.0 §7 rate-limiting dependency note is self-contradictory (Low, documented above).

No new High findings, no broken version references, and no DAG cycles were introduced by the patch.
