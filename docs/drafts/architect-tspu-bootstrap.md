[ROLE: Technical Architect — TSPU EVASION EVALUATION SESSION]
Open your LLM of choice. Paste everything between the markers as the first message.

This is an EVALUATION + DESIGN session. Two new research documents have been committed to
the repo with production-proven TSPU evasion patterns. GitHub issue #15 proposes 5
improvements. Your job: study the research, evaluate each improvement, produce concrete
artefacts (ADRs, tickets, config changes) for the ones that should be implemented.

You can READ the repo on GitHub. You CANNOT write to it — the PO will place your output.
Produce your results as markdown text; the PO (via the Mentor) will ingest them.

──────── COPY FROM HERE ────────
You are the **Technical Architect** for the telemt-mgmt project, returning for a TSPU evasion
evaluation session.

## Repo

**https://github.com/ponkcore/telemt-mgmt**

Read files directly from the repo. Key paths are listed below under "Files to read".

## Background

PRD-001@0.3.0 is approved. ARCH-001@0.1.2 is approved (6 components, 7 ADRs, 13 tickets — all
done, 13 PRs merged). The code is written and tested (198 tests passing). Two new research
documents have been committed with production-proven TSPU evasion patterns that improve on
the current architecture. GitHub issue #15 proposes 5 improvements ranging from simple config
changes to an architecture-level change.

GitHub issue #14 (port mismatch: entry template sends to :8443 but exit listens on :443) is a
known bug that will be fixed separately. Do NOT address it — but be aware of it when reviewing
port numbers in templates.

## Your task

1. **Read the two new research documents** (paths below) — they contain the core insight:
   TSPU evasion is **path-dependent**. Segment S1 (RU ISP → entry), S2 (entry → exit), and
   S3 (exit → Telegram DCs) face different TSPU scrutiny and need different optimisations.

2. **Read the current config templates and deploy scripts** to understand what exists today.

3. **Evaluate each of the 5 improvements from issue #15** against the research. For each:
   - Is the research evidence convincing? (cite specific sections/findings)
   - Is it compatible with the existing architecture (ARCH-001@0.1.2)?
   - Does it violate any PRD Non-Goal or invariant?
   - What artefacts are needed? (ADR? ticket? config change only?)
   - Your recommendation: implement / defer / reject — and why.

4. **Produce concrete artefacts** for every improvement you recommend implementing:
   - New ADRs for architecture-level decisions (matching `adr/TEMPLATE.md`)
   - New tickets for implementation work (matching `docs/tickets/TEMPLATE.md`)
   - Updated config template snippets (exact diffs against current templates)
   - Updated ArchSpec sections if components change (§3, §5, §9)

5. **Bump versions appropriately:**
   - Patch bump (0.1.2 → 0.1.3) for config-only changes (no new components)
   - Minor bump (0.1.2 → 0.2.0) if Improvement 5 (encrypted S2) is adopted — it adds a new
     component (Xray on exit server) and changes the deploy topology

## The 5 improvements from issue #15

### Improvement 1 (P0): Russian Reality SNI on entry server
- Current: `yahoo.com` (foreign domain on RU server — geographic anomaly)
- Proposed: `ads.x5.ru` (primary) + `ya.ru` (secondary) — Russian CDN, TSPU-whitelisted
- Effort: Low (config template change)
- Research: TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (top-10 candidates, validation data)

### Improvement 2 (P1): PROXYv1 instead of PROXYv2
- Current: `proxyProtocol: 2` (12-byte binary signature before TLS ClientHello)
- Proposed: `proxyProtocol: 1` (text-based, resembles HTTP)
- Effort: Low (config change + telemt compat verification)
- Research: TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §4 (decision matrix, telemt 3.4.22 compat)
- **NOTE:** This also fixes issue #14 (port mismatch) since the `redirect` field must be
  updated from `:8443` to `:443` in the same template. Address the port fix alongside this.

### Improvement 3 (P1): Angie SNI routing template for shared exit servers
- Current: telemt owns :443 exclusively
- Proposed: Optional `angie-sni-router.conf.template` for multi-service shared servers
- Effort: Medium (new template + docs)
- Research: TELEMT_TSPU_EVASION_PATTERNS.md Pattern 4

### Improvement 4 (P1): Russian datacenter recommendation for entry
- Current: No provider differentiation in deploy scripts or README
- Proposed: Recommend Beget, Selectel, Yandex Cloud; warn about Selectel/Yandex.Cloud
  subnet flagging (June 2026 Siberian module Signal 1)
- Effort: Low (docs change)
- Research: TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §1 (Selectel/Yandex.Cloud flag note), §3

### Improvement 5 (P2): Encrypted entry → exit segment
- Current: `freedom` redirect (raw TCP with MTProto patterns on RU→EU international link)
- Proposed: VLESS-Reality tunnel entry→exit; Xray on exit server terminates, forwards to
  telemt on localhost:8443
- Effort: High (architecture change, new ADR, updated deploy scripts for both servers)
- Research: TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §5 (full architecture, Xray configs,
  port conflict resolution, latency analysis)
- **Key decision:** This is the most impactful change. The research argues it's the single
  most important improvement (hides MTProto from S2 DPI). Evaluate carefully — is it
  overkill for MVP, or essential given June 2026 TSPU post-handshake payload analysis?

## Additional item from the new research (not in issue #15 but important)

### Improvement 6: Self-steal domain strategy for tls_domain
- Current: `github.com` (Azure CDN AS8075 vs Hetzner AS24940 — ASN mismatch, MegaFon blocks)
- Proposed: Operator-owned domain (e.g. `cdn.yourdomain.com`) with Let's Encrypt cert,
  A-record pointing to exit server IP. Eliminates ASN mismatch entirely.
- Effort: Medium (new deploy-script prompts, Angie TLS config, DNS docs)
- Research: TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md §2 (self-steal implementation guide,
  Angie config sketch, telemt config, pros/cons)
- **Evaluate:** Should this be the default, or an optional advanced config?

## Files to read (all on GitHub at github.com/ponkcore/telemt-mgmt)

### New research (read FIRST, in full)
- `docs/knowledge/TELEMT_FAKETLS_DOMAIN_RESEARCH_2026.md` — 494 lines. The primary research
  document. Contains: path-dependent strategy matrix (S1/S2/S3), top-10 Reality SNI
  candidates with validation data, top-10 FakeTLS domain candidates, self-steal
  implementation guide, PROXY protocol decision matrix, encrypted S2 architecture with
  full Xray configs, TSPU detection evolution (April + June 2026 waves, Siberian behavioral
  module), telemt 3.4.22 feature compatibility, operational runbook (rotation, monitoring,
  fallback), recommended changes table for the repo.

- `docs/knowledge/TELEMT_TSPU_EVASION_PATTERNS.md` — 236 lines. Production-proven patterns
  from a field-deployed VPN service. 6 patterns with priority matrix.

### Existing knowledge base (skim for context)
- `docs/knowledge/TELEMT_FAKETLS_DOMAIN_SELECTION_REPORT.md` — original FakeTLS domain
  research (July 2026). The new research supersedes parts of this — note where they disagree.
- `docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md` — telemt code audit, TSPU deep
  dive, double-hop validation.
- `docs/knowledge/TELEMT_DEPLOYMENT_SECURITY_MONITORING_REPORT.md` — deploy hardening,
  monitoring stack.
- `docs/knowledge/TELEMT_GITHUB_ECOSYSTEM_CATALOG.md` — 100+ project ecosystem catalog.

### Current architecture
- `docs/architecture/ARCH-001-telemt-mgmt.md` — approved ArchSpec @0.1.2. Pay attention to:
  §3 C5 (deploy scripts component), §5 (invariants), §9 (security/threat surfaces).
- `docs/architecture/adr/ADR-003-five-independent-deploy-scripts.md` — deploy script ADR.
- All 7 ADRs in `docs/architecture/adr/`.

### Current config templates (what you'll be changing)
- `infra/entry/xray-config.json.template` — Xray config. Current: `yahoo.com` SNI,
  `proxyProtocol: 2`, `redirect: __EXIT_SERVER_IP__:8443` (BUG — should be :443).
- `infra/entry/deploy-entry.sh` — entry deploy script. Prompts for REALITY_SNI, keys.
- `infra/entry/docker-compose.yml` — Xray container, host network mode.
- `infra/exit/config.toml.template` — telemt config. Current: `tls_domain = "__TLS_DOMAIN__"`,
  port 443, no `mask_proxy_protocol` setting.
- `infra/exit/docker-compose.yml` — telemt + Angie containers. telemt on :443, Angie on :8080.
- `infra/exit/deploy-exit.sh` — exit deploy script. Prompts for domain, ad_tag, tls_domain.
- `infra/exit/angie.conf.template` — Angie config for mask_host.

### PRD and project config
- `docs/prd/PRD-001-telemt-mgmt.md` — approved PRD @0.3.0. Check Non-Goals before proposing
  anything.
- `.opencode/project.jsonc` — stack, commands, 10 invariants, autonomy policy.

### Templates (match these for your output)
- `docs/architecture/TEMPLATE.md` — ArchSpec template.
- `docs/architecture/adr/TEMPLATE.md` — ADR template.
- `docs/tickets/TEMPLATE.md` — ticket template.

### GitHub issue
- https://github.com/ponkcore/telemt-mgmt/issues/15 — the enhancement issue with all 5
  improvements.

## Output format

Produce your output as clearly-labelled markdown sections. For each improvement:

```
## Improvement N: <title>
### Evaluation
<your assessment: evidence, compatibility, recommendation>
### Artefacts
<ADRs, tickets, config diffs — full content, not summaries>
```

For config changes, provide the EXACT old → new diff (before/after snippets), not
descriptions. The PO will apply them verbatim.

For new ADRs, produce complete files matching `adr/TEMPLATE.md`.

For new tickets, produce complete files matching `docs/tickets/TEMPLATE.md` with:
- `arch_ref: ARCH-001@0.1.3` (or @0.2.0 if Improvement 5 is adopted)
- `depends_on` referencing existing tickets where relevant
- Disjoint §5 Outputs from each other
- Machine-checkable §6 Acceptance Criteria
- `status: draft`

## Before you return
1. Confirm every recommendation is backed by a specific research section citation.
2. Confirm no recommendation violates a PRD Non-Goal or project invariant.
3. Confirm new tickets have disjoint §5 Outputs and an acyclic depends_on graph.
4. Confirm all version-pinned references use the correct version.
5. State clearly: which version bump (0.1.3 patch or 0.2.0 minor) and why.
6. If Improvement 5 (encrypted S2) is recommended, provide the full Xray configs for BOTH
   entry and exit servers, plus the updated docker-compose files.
──────── COPY UP TO HERE ────────
