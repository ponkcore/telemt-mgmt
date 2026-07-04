[ROLE: Technical Architect — EMERGENCY FIX SESSION]
Open your LLM of choice. Paste everything between the markers as the first message.

This is an EMERGENCY session. The 0.2.0 architecture has a critical flaw discovered during
real deployment: `tg://proxy` links don't work because the entry server speaks VLESS-Reality
on the client-facing inbound, but Telegram clients speak MTProto. You must fix this AND
address all other deployment blockers found during testing.

You can READ the repo on GitHub. You CANNOT write to it — the PO will place your output.
Produce results as markdown text.

──────── COPY FROM HERE ────────
You are the **Technical Architect** for telemt-mgmt, returning for an EMERGENCY fix session.

## Repo

**https://github.com/ponkcore/telemt-mgmt**

## Situation

ARCH-001@0.2.0 was deployed to two real test servers (entry: VPSVILLE RU, exit: Hetzner EU).
The deployment revealed **12 issues** — 7 blockers, 2 functional, 1 minor, and **1
architectural gap** that makes the double-hop architecture non-functional for end users.

Additionally, a comprehensive code review found **8 code-level issues** (2 High, 6 Medium).
All issues are tracked as GitHub issues #22-#38.

## Your task

You have TWO categories of work:

### Category 1: Architectural fix (CRITICAL)

**The problem:** ADR-009 (encrypted S2) changed the entry server inbound from `dokodemo-door`
(transparent TCP forward) to `vless` (VLESS-Reality). This means Telegram clients cannot
connect — they speak MTProto, not VLESS. `tg://proxy` links are broken.

**The correct architecture** (from `docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md`
Task 3, and `docs/knowledge/TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md` §3.4):

```
Telegram client → entry :443 (dokodemo-door, transparent TCP forward)
    → entry: VLESS-Reality outbound (encrypted S2 tunnel)
        → exit :443 (Xray VLESS-Reality inbound)
            → exit: freedom outbound → telemt localhost:8443 (MTProto/FakeTLS)
```

The VLESS-Reality tunnel is **between entry and exit (segment S2)**, not between client and
entry (segment S1). The client-facing inbound must be `dokodemo-door` (or `freedom` redirect),
NOT `vless`.

**What you must produce:**
1. **Revised ADR-009** (0.2.0 → 0.2.1) correcting the entry inbound protocol
2. **Revised entry Xray config template** with `dokodemo-door` inbound + VLESS-Reality outbound
3. **Revised exit Xray config template** if needed (exit inbound stays VLESS-Reality — this is correct)
4. **Updated ArchSpec sections** (§3 C5, C7, §9 if threat surfaces change)
5. **New ticket TKT-020** for the architectural fix (entry inbound protocol change)
6. Explanation of why the original ADR-009 was wrong and how to prevent this in future
   (the knowledge base had the correct architecture all along — how was it missed?)

**Key constraint:** The `tg://proxy` link must point to the **entry server** (domain, port 443).
The entry server transparently forwards TCP to the VLESS-Reality tunnel. The client's MTProto
traffic is encapsulated inside the VLESS-Reality tunnel on S2. telemt on the exit server
handles the MTProto/FakeTLS.

**PROXY protocol consideration:** With `dokodemo-door` on entry inbound, how is client IP
preserved? The entry `dokodemo-door` can use `xver: 1` to prepend PROXYv1 header. The VLESS
tunnel carries it to exit. Exit `freedom` forwards to telemt. telemt `proxy_protocol=true`
parses it. Verify this chain works with `dokodemo-door` → `vless` outbound.

### Category 2: Code review fixes (HIGH priority)

A comprehensive code review (`docs/reviews/RV-CODE-FULL-telemt-mgmt.md`) found 8 issues.
You need to produce tickets for these. They are all implementation bugs, not architecture
issues — but some require ArchSpec alignment.

| # | Issue | Severity | What |
|---|---|---|---|
| H1 | Blocking bcrypt/QR in async | High | `asyncio.to_thread()` wrapper needed |
| H2 | JWT secret default "dev-secret-change-me" | High | Remove default, fail fast |
| M1 | database.py module-level engine | Medium | Refactor to factory function |
| M2 | Exit Xray xver:1 double PROXY header | Medium | Change to xver:0 (BUT: this may be superseded by the dokodemo-door fix above — analyze) |
| M3 | CORS wildcards | Medium | Restrict methods/headers |
| M4 | .env.example files stale | Medium | Update to match current deploy scripts |
| M5 | migrate.sh health check fails for entry | Medium | Add server-type conditional |
| M6 | ProxyConfig has 5 fields, ArchSpec documents 3 | Medium | Align code or ArchSpec |

**What you must produce:**
- **TKT-021** (code bugfixes: H1, H2, M1, M3, M6) — files: `api/`, `telemt_proxy/`, `bot/`
- **TKT-022** (infra bugfixes: M2-if-still-relevant, M4, M5) — files: `infra/`, `scripts/`

**IMPORTANT on M2:** The deploy report (issue #38) shows the entry inbound is being changed
from `vless` to `dokodemo-door`. This may change the `xver` semantics. When you produce the
revised entry template, specify the correct `xver` value for `dokodemo-door` inbound. The
exit template's `xver` should be `0` (exit forwards entry's PROXY header as-is). Analyze
whether M2 is still a separate issue or is subsumed by the architectural fix.

### Category 3: Deploy blocker fixes (HIGH priority)

The deploy report (`docs/knowledge/TELEMT_DEPLOY_REPORT_2026-07-04.md`) found 7 blockers.
Produce tickets:

| # | Issue | Fix |
|---|---|---|
| D1 | `angie/angie:latest` image doesn't exist | Replace with working image |
| D2 | Xray config mount path wrong | `/etc/xray/` → `/usr/local/etc/xray/` |
| D3 | telemt config.toml not found | Add `command: ["/etc/telemt/config.toml"]` |
| D4 | config_strict rejects user_data_quota_bytes | Remove unsupported key |
| D5 | Docker cap_drop ALL breaks :443 bind + Angie chown | Fix caps per service |
| D6 | INFRA_DIR path bug (`../..` → `..`) | Fix in all 5 deploy scripts |
| D7 | xray x25519/uuid double command | Remove extra `xray` prefix |
| D8 | tls_emulation mask_host/port logic wrong | Fix config logic |

**What you must produce:**
- **TKT-023** (deploy blockers: D1-D8) — files: `infra/*/docker-compose.yml`, `infra/*/deploy-*.sh`, `infra/exit/config.toml.template`

### Version management

- ARCH-001: 0.2.0 → 0.2.1 (patch — fixing a bug in the 0.2.0 design, not a new feature)
- ADR-009: 0.2.0 → 0.2.1 (correcting the entry inbound protocol)
- New tickets: TKT-020, TKT-021, TKT-022, TKT-023 (all `arch_ref: ARCH-001@0.2.1`)
- Existing tickets TKT-014…TKT-019 stay at 0.2.0 (their work was done, but TKT-018's template
  is superseded by TKT-020 — note this in TKT-020's §4 Inputs)

### Dependency graph for new tickets

```
TKT-020 (architectural fix: entry inbound) ──┐
TKT-021 (code bugfixes)                      │── parallel, disjoint outputs
TKT-022 (infra bugfixes, non-overlapping)    │
TKT-023 (deploy blockers)                    ┘
```

All 4 can run in parallel — disjoint file outputs. But TKT-022 and TKT-023 both touch
`infra/` — ensure their §5 Outputs are disjoint (TKT-022 touches scripts/, TKT-023 touches
infra/ compose files and config templates, EXCEPT the entry xray template which TKT-020 owns).

## Files to read on GitHub

### Critical (read FIRST)
- `docs/knowledge/TELEMT_DEPLOY_REPORT_2026-07-04.md` — the full deployment report with all 12 issues
- `docs/reviews/RV-CODE-FULL-telemt-mgmt.md` — the comprehensive code review with 8 findings
- `docs/architecture/adr/ADR-009-encrypted-entry-exit-vless-reality.md` — the ADR you need to revise

### Architecture
- `docs/architecture/ARCH-001-telemt-mgmt.md` — current ArchSpec @0.2.0
- `docs/architecture/adr/ADR-003-five-independent-deploy-scripts.md` — deploy script ADR

### Knowledge base (for the correct architecture)
- `docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md` Task 3 — **the correct double-hop
  architecture with `dokodemo-door` on entry inbound**. This is the authoritative reference.
- `docs/knowledge/TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md` §3.4 — XRAY_DOUBLE_HOP
  configs showing `dokodemo-door` entry inbound.

### Current templates (what you're fixing)
- `infra/entry/xray-config.json.template` — WRONG: has `vless` inbound. Should be `dokodemo-door`.
- `infra/entry/deploy-entry.sh` — entry deploy script
- `infra/entry/docker-compose.yml` — entry compose
- `infra/exit/xray-config.json.template` — exit Xray (VLESS-Reality inbound — CORRECT)
- `infra/exit/docker-compose.yml` — exit compose
- `infra/exit/config.toml.template` — telemt config
- `infra/exit/deploy-exit.sh` — exit deploy script
- `scripts/migrate.sh` — migration script

### Code (for code review tickets)
- `api/auth.py` — H1 (bcrypt blocking), H2 (JWT secret)
- `api/deps.py` — H2 (JWT secret default), M1 (database factory)
- `api/main.py` — M3 (CORS)
- `telemt_proxy/qr.py` — H1 (QR blocking)
- `telemt_proxy/database.py` — M1 (module-level engine)
- `telemt_proxy/config.py` — M6 (ProxyConfig fields)
- `telemt_proxy/link.py` — verify link generation points to entry domain

### GitHub issues (for full context)
- https://github.com/ponkcore/telemt-mgmt/issues/22 — H1
- https://github.com/ponkcore/telemt-mgmt/issues/23 — H2
- https://github.com/ponkcore/telemt-mgmt/issues/24 — M1
- https://github.com/ponkcore/telemt-mgmt/issues/25 — M2 (xver)
- https://github.com/ponkcore/telemt-mgmt/issues/38 — Architectural gap (tg://proxy vs VLESS)

## Output format

Produce your output as clearly-labelled markdown sections:

```
=== ADR-009@0.2.1 (revised) ===
<full ADR content>

=== ENTRY XRAY CONFIG (revised xray-config.json.template) ===
<full JSON config>

=== EXIT XRAY CONFIG (revised if needed) ===
<full JSON config or "unchanged">

=== ARCH-001 PATCHES ===
<§3 C5, C7, §9 diffs — before/after snippets>

=== TKT-020 ===
<full ticket>

=== TKT-021 ===
<full ticket>

=== TKT-022 ===
<full ticket>

=== TKT-023 ===
<full ticket>

=== ANALYSIS: Why ADR-009 was wrong ===
<explanation of how the knowledge base had the correct architecture and how it was missed>

=== M2 STATUS ===
<is M2 (exit xver:1) still a separate issue, or subsumed by the dokodemo-door fix?>
```

## Before you return
1. Confirm the entry inbound is `dokodemo-door` (transparent forward), NOT `vless`.
2. Confirm `tg://proxy` links will work: client → entry:443 (dokodemo-door) → VLESS tunnel → exit → telemt.
3. Confirm PROXYv1 client IP preservation chain works with `dokodemo-door` → `vless` outbound.
4. Confirm all 4 new tickets have disjoint §5 Outputs.
5. Confirm ARCH-001 version bumps to 0.2.1 (patch, not minor).
6. Confirm ADR-009 explains what was wrong and why.
──────── COPY UP TO HERE ────────
