---
id: RV-CODE-011
type: code_review
target_pr: "https://github.com/ponkcore/telemt-mgmt/pull/7"
ticket_ref: TKT-011@0.1.1
status: in_review
created: 2026-07-03
---

# RV-CODE-011: review of TKT-011@0.1.1 (PR #7)

**Verdict:** pass_with_changes  
**Summary:** The monitoring deploy script and Docker Compose meet all six ACs and respect `INV-DOCKER`/`INV-IDEMPOTENT`; one Medium finding (Grafana datasource UID should match the dashboards) and a handful of Low clean-up items need fixing or backlog.

## Contract compliance
- [x] Diff modifies ONLY §5 Outputs (+ ticket status/§10).
- [x] No §3 NOT-In-Scope term touched.
- [x] No unauthorised runtime dependency.
- [x] Every §6 AC verifiably met (citations below).
- [ ] project.jsonc checks green (typecheck/lint/test). *Lint/typecheck pass; `pytest` fails on a pre-existing environment issue (missing `libstdc++.so.6` for greenlet) that also fails on `main`, so it is not introduced by this PR.*
- [x] All project.jsonc invariants hold in the diff.

## Acceptance criteria
- **AC1 — idempotent** — `deploy-monitoring.sh:52-54` calls `load_env` then `prompt_for`; re-runs with an existing `.env` skip interactive prompts (INV-IDEMPOTENT).
- **AC2 — Prometheus scrapes telemt :9090** — `prometheus.yml.template:21-25` declares the `telemt` job using `__TELEMT_METRICS_ENDPOINT__`, replaced by the operator-supplied value at `deploy-monitoring.sh:90-92`.
- **AC3 — Grafana auto-provisions both dashboards** — `grafana/provisioning/datasources/prometheus.yml` + `grafana/provisioning/dashboards/dashboards.yml` + `grafana/dashboards/telemt-proxy-health.json` + `grafana/dashboards/telemt-per-user.json`.
- **AC4 — 10 alert rules** — `alert-rules.yml:12-119` defines all ten rules from `docs/knowledge/TELEMT_DEEP_GAPS_VERIFICATION_REPORT.md` §Task 7.
- **AC5 — Grafana admin password via env var** — `docker-compose.yml:51-52` uses `${GRAFANA_ADMIN_PASSWORD}`; `.env.example:11` documents it; `deploy-monitoring.sh:63-83` prompts or auto-generates and persists it to `.env`.
- **AC6 — shellcheck clean** — `shellcheck infra/monitoring/deploy-monitoring.sh` returns no output.

## Findings
### High  (block merge)
- none

### Medium  (fix or backlog)
- **F-M1:** `infra/monitoring/grafana/provisioning/datasources/prometheus.yml:9-13` — The provisioned Prometheus datasource omits a `uid`, while both dashboard JSONs hardcode datasource UID `PBFA97CFB590B2093`. Grafana will currently fall back to the default datasource, but this is fragile; add `uid: PBFA97CFB590B2093` to the datasource provisioning so the dashboards reliably bind to it.

### Low  (optional)
- **F-L1:** `infra/monitoring/docker-compose.yml:28` — Prometheus is configured with `--alertmanager.url=http://localhost:9093`, but no Alertmanager service is deployed (Alertmanager Telegram integration is deferred per TKT-011 §3). Either remove the flag or add a backlog ticket to deploy Alertmanager.
- **F-L2:** `infra/monitoring/alert-rules.yml:100-103` — `TelemtDiskSpaceLow` references `node_filesystem_*` metrics, but Node Exporter is not part of this deploy, so the rule can never fire. Backlog adding Node Exporter or remove the rule until the full node-exporter stack is in scope.
- **F-L3:** `infra/monitoring/.env.example:12` — Comment says "auto-generates a 16-byte hex password"; the script calls `generate_secret 16`, producing 16 bytes = 32 hex characters. Clarify the comment.
- **F-L4:** `infra/monitoring/prometheus.yml.template:28-31` — Self-monitoring target `localhost:9090` works inside the Prometheus container, but using the service name (`prometheus:9090`) would be clearer and consistent with the Grafana datasource.
- **F-L5:** `docs/tickets/TKT-011-deploy-monitoring.md:5` — `arch_ref: ARCH-001@0.1.1` is stale; the approved ArchSpec is `ARCH-001@0.1.2`.

## Red-team probes
- **error_paths:** `deploy-monitoring.sh:43` (`check_docker`) and `:77-79` (empty password) exit with an error message; good.
- **concurrency:** N/A — single-server deploy script.
- **input_validation:** `deploy-monitoring.sh:91` uses `sed` with an unquoted user-supplied endpoint; special characters (`&`, `\`, `|`) could corrupt `prometheus.yml`. In practice IP:port only, but F-M1-style sanitisation would be safer.
- **authz_isolation:** `docker-compose.yml:53` disables Grafana self-signup; admin password is environment-driven, not committed.
- **secrets:** `GRAFANA_ADMIN_PASSWORD` is stored only in `.env` (gitignored per INV-SECRETS); `.env.example` documents the variable with an empty value. No secrets in git.
- **observability:** Prometheus self-monitoring is present; Grafana auto-provisions datasource and dashboards; 10 alert rules defined.
- **rollback:** `docker compose down && up -d` on re-run updates configuration but does not provide a rollback path beyond re-running the script. Backlog a rollback note in runbooks.
- **dns_failover:** N/A — this ticket deploys the monitoring server, not proxy DNS.
