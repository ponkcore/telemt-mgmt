---
id: TKT-011
type: ticket
status: ready
arch_ref: ARCH-001@0.1.1
depends_on: [TKT-008@0.1.1]
estimate: M
created: 2026-07-02
---

# TKT-011@0.1.1: Deploy Script — Monitoring Server (Prometheus + Grafana)

## §1 Goal

Create an interactive deploy script and Docker Compose for the monitoring server running Prometheus + Grafana, scraping the exit server's telemt metrics.

## §2 In Scope

- `infra/monitoring/deploy-monitoring.sh` — interactive script. Prompts: telemt metrics endpoint (exit server IP:9090), Grafana admin password.
- `infra/monitoring/docker-compose.yml` — Prometheus + Grafana containers.
- `infra/monitoring/prometheus.yml.template` — Prometheus config scraping exit server :9090.
- `infra/monitoring/grafana/provisioning/` — dashboard provisioning (auto-import #25119 and per-user dashboard).
- `infra/monitoring/grafana/dashboards/` — grafana-dashboard.json and grafana-dashboard-by-user.json from telemt repo.
- Alert rules (10 alerts from knowledge base).

## §3 NOT In Scope

- Loki/Promtail log aggregation (deferred).
- Alertmanager Telegram webhook integration (deferred).
- Uptime Kuma (deferred).

## §4 Inputs

- ARCH-001@0.1.1 §3 C5 (deploy-monitoring.sh interface)
- ADR-003@0.1.1
- PRD-001@0.3.0 §5 R13
- docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md §Task 7 (monitoring stack, 10 alert rules)

## §5 Outputs

- `infra/monitoring/deploy-monitoring.sh`
- `infra/monitoring/docker-compose.yml`
- `infra/monitoring/prometheus.yml.template`
- `infra/monitoring/alert-rules.yml`
- `infra/monitoring/grafana/provisioning/datasources/prometheus.yml`
- `infra/monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `infra/monitoring/grafana/dashboards/telemt-proxy-health.json`
- `infra/monitoring/grafana/dashboards/telemt-per-user.json`
- `infra/monitoring/.env.example`

## §6 Acceptance Criteria

- [ ] AC1 — `deploy-monitoring.sh` is idempotent.
- [ ] AC2 — Prometheus scrapes telemt :9090 endpoint (configurable).
- [ ] AC3 — Grafana auto-provisions both dashboards on first start.
- [ ] AC4 — All 10 alert rules defined in `alert-rules.yml`.
- [ ] AC5 — Grafana admin password set via env var (not default).
- [ ] AC6 — `shellcheck infra/monitoring/deploy-monitoring.sh` passes.

## §7 Constraints

- Prometheus image: `prom/prometheus:v2.54.1`.
- Grafana image: `grafana/grafana:12.4.2` (required for dashboard #25119 compatibility, published 2026-04-06, requires Grafana 12.4.2+).

## §8 Definition of Done

- [ ] All §6 AC met.
- [ ] project.jsonc checks green.
- [ ] Reviewer verdict pass / pass_with_changes.
- [ ] docs-ci green.

## §10 Execution Log

- 2026-07-02 architect: ticket created.
- 2026-07-02 architect: patched per RV-ARCH-001 finding M7 (Grafana image corrected to 12.4.2 for dashboard #25119 compatibility).
