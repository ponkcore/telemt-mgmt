---
id: ARCH-NNN
type: arch_spec
status: draft        # draft → in_review → approved → superseded
version: 0.1.0
prd_ref: PRD-NNN@X.Y.Z
adrs: [ADR-NNN@X.Y.Z]
tickets: [TKT-NNN@X.Y.Z]
created: YYYY-MM-DD
---

# ARCH-NNN: <Title>

## §0 Recon Report  *(mandatory — Phase 0)*

> Written BEFORE design. Read everything in `docs/knowledge/` and audit fork/reuse
> candidates. An ArchSpec without this section is rejected.

- **Knowledge consulted:** <files in docs/knowledge/ you read>
- **Reuse / fork candidates evaluated:** <libs, prior components, internal modules>
- **Decision:** build / fork / adopt — and why.

## §1 Overview

<What this spec designs and how it satisfies the PRD. One paragraph.>

## §2 Goal Coverage

| PRD Goal | Covered by Component(s) |
|---|---|
| G1 | C1 |
| G2 | C2, C3 |

(Every PRD `§2` goal must map to ≥1 component. The architecture-reviewer checks this.)

## §3 Components

### C1 — <name>
- **Responsibility:** <…>
- **Interface / contract:** <inputs, outputs, error modes>
- **Depends on:** <other components / external services>
- **Relevant ADRs:** <ADR-NNN@X.Y.Z>

### C2 — <name>
- …

## §4 Data & Interfaces

<Schemas, key types, API contracts. Keep shared interface definitions here so tickets
reference one source of truth.>

## §5 Cross-cutting Invariants

<Anything that becomes a `project.jsonc.invariants` entry: security boundaries, tenancy,
sanitisation surfaces, observability conventions. State them once; tickets enforce them.>

## §6 Sequencing

<Build order across components; which ticket-clusters can run in parallel (disjoint outputs).>

## §9 Security

<Threat surfaces, secrets handling (env vars only, `.env.example`), authz/isolation model.>

## §Revision Log
- YYYY-MM-DD 0.1.0 — initial draft.
