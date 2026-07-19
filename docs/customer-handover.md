# Customer Handover

This document is the maintained customer handover guide for Tickframe during
Assignment 6. It describes the actual Week 6 handover baseline and the concrete
steps a customer, TA, or teammate can inspect without exposing private access
details.

Private credentials, exact recording timecodes, customer-identifying evidence,
and private access instructions must stay out of this public repository. Put
those details only in the Week 6 or Week 7 Moodle PDF submission wrapper.

## Current Handover State

As of the Week 6 handover baseline, the Tickframe repository and public
run/handover instructions have been transferred to the customer as public GitHub
links. The customer can review, clone, run, and inspect the product from the
documented release and repository entry points. The team still retains
administrative control of the protected repository, release process, public
deployment decisions, and any private credentials until final Week 7 transition
confirmation is completed.

Current status:

- Handover baseline: Week 6 trial / handover-candidate documentation.
- Repository and public instructions: transferred to the customer.
- Current public product access artifact: [Tickframe MVP v2.0.0 release](https://github.com/Team-29-TickFrame/Tickframe_team_29/releases/tag/v2.0.0).
- Final MVP v3 release and final customer confirmation: pending Week 7 follow-up
  work and tracked separately through the Assignment 6 Sprint 5 issues.
- Customer-side independent operation or deployment: not confirmed in this
  Week 6 baseline.

This document is sufficient for a guided Week 6 trial, TA inspection, and local
or VM/VPS-based handover rehearsal. Final handover level and customer
confirmation status must be updated after Week 7 confirmation.

## Customer-Facing Entry Points

- Repository front page: [README.md](../README.md)
- Current hosted documentation site:
  <https://team-29-tickframe.github.io/Tickframe_team_29/>
- Contributing workflow: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Agent-facing repository guidance: [AGENTS.md](../AGENTS.md)
- Roadmap and Sprint 4 / Sprint 5 scope: [docs/roadmap.md](roadmap.md)
- Architecture overview: [docs/architecture/README.md](architecture/README.md)
- Testing and quality status: [docs/testing.md](testing.md)
- User acceptance tests: [docs/user-acceptance-tests.md](user-acceptance-tests.md)
- Backend details and API behavior: [backend/README.md](../backend/README.md)
- Runtime configuration template: [.env.example](../.env.example)
- Docker Compose runtime: [docker-compose.yml](../docker-compose.yml)

The Week 6 report index will be `reports/week6/README.md` when published. The
Week 7 final Assignment 6 submission index will be `reports/week7/README.md`
when published.

## Transfer, Delegation, and Retention

| Area | Current arrangement | Customer impact |
| --- | --- | --- |
| Source repository | Public GitHub repository link has been transferred to the customer. Protected branch control and merge/release permissions remain with the team during Week 6. | Customer and TA can review, clone, and run the product; repository administration remains with the team in this baseline. |
| Public instructions | README, handover, setup, and documentation entry-point links have been transferred to the customer. | Customer can follow the public run and review instructions without needing private credentials. |
| Trial run responsibility | Public local/VM run instructions are delegated to the customer for Week 6 trial and review. | Customer can attempt the documented run path independently or with light team support. |
| Product access | Public release artifact points reviewers to the current runnable code and instructions. Any private live access details stay in Moodle/private channels. | Customer can use the documented local or hosted access path without exposing credentials publicly. |
| Runtime stack | `docker-compose.yml` defines frontend, backend, TimescaleDB, Prometheus, and Grafana. | Customer can reproduce the maintained runtime on a local machine or Linux VM/VPS with Docker. |
| Deployment operation | Team retains responsibility for public deployment setup, reverse proxy details, backups, and secrets during Week 6. | Customer-side deployment is possible from the guide, but final ownership/operation is not confirmed yet. |
| Data sources | Binance and Bybit public Spot market data are used; no exchange API keys are required for the maintained public streams. | Customer does not need exchange credentials for the current live-data workflow. |
| Database and volumes | TimescaleDB runs inside the Compose network with persistent Docker volumes. | Customer must preserve Docker volumes or backups when operating the product beyond a demo run. |
| Observability | Prometheus and Grafana are included in the Compose stack. Grafana anonymous viewer access is enabled for demo inspection. | Customer can inspect health, latency, freshness, and market observability without direct database access. |
| Secrets and credentials | `.env.example` contains safe examples only. Real `.env` values are retained privately. | Customer receives private credentials only through approved private handover/submission channels. |
| Unavailable public details | Direct database credentials, private live URLs, private recordings, exact timecodes, and customer-identifying evidence are unavailable in the public repository by design. | Customer and instructors receive any necessary private details through the approved private channel, not through GitHub. |
| Final acceptance | Week 7 customer confirmation is not part of this Week 6 baseline. | Final handover level and acceptance status must be recorded after the Week 7 confirmation step. |

## Configuration and Secrets

Create a private `.env` file from [.env.example](../.env.example). Never commit
the real `.env` file.

Required or important values:

- `POSTGRES_PASSWORD`: required for TimescaleDB. Replace the placeholder with a
  strong private value.
- `BACKEND_PORT`, `FRONTEND_PORT`, `PROMETHEUS_PORT`, `GRAFANA_PORT`: optional
  host port overrides when defaults conflict with another local service.
- `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`: optional Grafana bootstrap
  admin credentials. The public example uses demo-safe values only.
- `TICKFRAME_BINANCE_WS_URLS`, `TICKFRAME_BYBIT_WS_URLS`,
  `TICKFRAME_BINANCE_REST_URLS`, `TICKFRAME_BYBIT_REST_URLS`: optional endpoint
  fallback overrides for networks where an exchange domain is blocked or
  unstable.
- `TICKFRAME_RECOVERY_BACKFILL_HOURS`,
  `TICKFRAME_DISABLE_RECOVERY_BACKFILL`,
  `TICKFRAME_BINANCE_1S_BACKFILL_HOURS`, and
  `TICKFRAME_SECOND_REPAIR_HOURS`: recovery and historical backfill controls.
- `TICKFRAME_STABLE_CHART_DELAY_MS`: stable short-timeframe chart delay for late
  exchange messages.
- `TICKFRAME_PATTERN_CONFIDENCE_THRESHOLD`: threshold for the experimental
  `1m` ML pattern detector.
- `TICKFRAME_SHUTDOWN_TIMEOUT`: graceful backend queue-drain timeout.

The backend receives `DATABASE_URL` from Docker Compose. A customer running the
backend outside Compose must provide a compatible PostgreSQL/TimescaleDB
connection string or accept the limited in-memory fallback described in
[backend/README.md](../backend/README.md).

## Setup and Local Trial Run

Prerequisites:

- Docker and Docker Compose.
- Network access to public Binance and Bybit endpoints, or configured endpoint
  fallbacks in `.env`.
- Enough local disk space for Docker images and TimescaleDB volumes.

Steps:

1. Clone or download the repository.
2. Create the private runtime file:

   ```bash
   cp .env.example .env
   ```

3. Replace the example `POSTGRES_PASSWORD` and any other private values in
   `.env`.
4. Start the full product:

   ```bash
   docker compose up --build
   ```

5. Open the main services:

   - Frontend: <http://127.0.0.1:4173>
   - API docs: <http://127.0.0.1:8000/docs>
   - Health check: <http://127.0.0.1:8000/health>
   - Prometheus: <http://127.0.0.1:9090>
   - Grafana dashboard: <http://127.0.0.1:3000/d/tickframe-latency/tickframe-latency>

6. Stop the stack when finished:

   ```bash
   docker compose down
   ```

Docker volumes are preserved after `docker compose down`. Removing Docker
volumes deletes stored TimescaleDB, Prometheus, and Grafana state.

## Optional Historical Loading

The live product starts from public market streams and also performs recent
recovery backfill. For a richer review window, load public historical candles
after the stack is running:

```bash
docker compose exec backend python -m backend.scripts.backfill_candles --days 30
docker compose exec backend python -m backend.scripts.history --days 30
docker compose exec backend python -m backend.scripts.history --exchange binance --timeframe 1s --days 1
```

These commands are safe to rerun. Existing candle keys are updated instead of
duplicated.

## Server Deployment Baseline

The maintained deployment shape is Docker Compose on a Linux VM or VPS. Shared
static hosting is not enough because Tickframe needs Python collectors,
WebSocket services, TimescaleDB, Prometheus, and Grafana.

Deployment baseline:

1. Provision a Linux host with Docker and Docker Compose.
2. Copy or clone the repository to the host.
3. Create a private `.env` with production-grade values.
4. Start the stack:

   ```bash
   docker compose up -d --build
   ```

5. Put a host-level reverse proxy in front of the frontend for public HTTPS and
   WSS access.
6. Keep TimescaleDB private to the Docker network.
7. Keep Docker volumes persistent and configure host-level backups for any
   long-running customer operation.
8. Synchronize the server clock with NTP so latency and freshness measurements
   remain meaningful.
9. Record final public access URLs and any private credentials only in the
   appropriate Week 6 or Week 7 private submission channel.

## Verification Checklist

Run these checks before declaring a Week 6 trial or handover candidate ready:

- Frontend opens at <http://127.0.0.1:4173>.
- API health returns successfully at <http://127.0.0.1:8000/health>.
- API docs open at <http://127.0.0.1:8000/docs>.
- Candles endpoint returns data for a supported instrument, for example
  <http://127.0.0.1:8000/api/v1/candles?exchange=binance&instrumentId=BTC-USDT&timeframe=1m&limit=100>.
- Metrics endpoint returns analytics, for example
  <http://127.0.0.1:8000/api/v1/metrics?exchange=binance&instrumentId=BTC-USDT&timeframe=1m&limit=300>.
- Prometheus metrics are available at <http://127.0.0.1:8000/metrics>.
- Human latency snapshot opens at
  <http://127.0.0.1:8000/api/v1/observability/latency>.
- Grafana dashboard opens at
  <http://127.0.0.1:3000/d/tickframe-latency/tickframe-latency>.
- The UI can switch exchange, instrument, and timeframe without mixing Binance
  and Bybit into synthetic data.
- Customer-facing UAT scenarios in
  [docs/user-acceptance-tests.md](user-acceptance-tests.md) are reviewed or
  executed where practical.

## Operation Notes

- Tickframe is a read-only market analytics and pattern-analysis product. It
  does not execute trades and does not provide buy/sell advice.
- Binance and Bybit are intentionally kept as independent sources in
  configuration, storage, APIs, and UI state.
- Short timeframes (`1s`, `5s`, `15s`) use a stable display delay so late
  exchange messages can revise recent candles instead of being hidden.
- Bybit Spot REST does not expose historical `1s` klines. Bybit second charts
  use locally captured live trades when available and may explicitly fall back
  to Binance `1s` historical candles as a proxy source.
- Raw trades are retained for 72 hours, `1s` candles for 14 days, and aggregated
  longer timeframes are retained for long-term analysis.
- Metric events and ML pattern output are analysis aids. They should be
  presented as confidence/visibility signals, not trading instructions.

## Recovery and Troubleshooting

Use this section when the trial run or deployment behaves unexpectedly.

| Symptom | Likely cause | Recovery action |
| --- | --- | --- |
| Backend health check fails | Backend cannot connect to TimescaleDB, migrations are still running, or `.env` has an invalid value. | Check Compose service status and backend logs; verify `POSTGRES_PASSWORD`; restart with `docker compose up -d --build --force-recreate backend`. |
| Frontend opens but data is stale or empty | Exchange endpoint is blocked, collectors are reconnecting, or historical backfill has not populated the selected window yet. | Check `/api/v1/observability/latency`; configure exchange fallback URLs in `.env`; run the optional historical loading commands. |
| Grafana opens but panels are empty | Prometheus has not scraped enough samples yet or backend metrics are unavailable. | Wait for new samples, verify <http://127.0.0.1:8000/metrics>, and check Prometheus at <http://127.0.0.1:9090>. |
| Short-timeframe candles look delayed | This is expected stable-candle behavior for late exchange messages. | Adjust `TICKFRAME_STABLE_CHART_DELAY_MS` only if the customer's network consistently delays exchange messages. |
| Latency values look unrealistic | Host or browser clocks may be out of sync. | Synchronize the server with NTP and document browser clock skew as a measurement limitation. |
| Local ports are already in use | Another service is using the default frontend, backend, Prometheus, or Grafana ports. | Set `FRONTEND_PORT`, `BACKEND_PORT`, `PROMETHEUS_PORT`, or `GRAFANA_PORT` in `.env`, then recreate the stack. |
| Stored history disappears after cleanup | Docker volumes were removed. | Restore from host-level backups if available; otherwise rerun public historical loading where exchange APIs support it. |

For code or workflow changes, follow [CONTRIBUTING.md](../CONTRIBUTING.md) and
keep issue links, review evidence, and CI checks inspectable before merge.

## Support Expectations

During the Week 6 trial baseline, the team remains responsible for:

- clarifying setup, access, and deployment instructions;
- helping the customer or TA interpret dashboard, metrics, and observability
  output;
- converting customer-visible product, deployment, documentation, or handover
  problems into traceable PBIs/issues;
- keeping this document current when access, deployment, limitations, or
  transition status changes;
- preserving private evidence only in approved private channels.

The customer or TA has the repository and public instructions needed to inspect
the project, run the Compose stack, open the frontend/API/Grafana surfaces, and
review the maintained documentation from the links above. Independent customer
operation, customer-side deployment, and final acceptance are not claimed by
this Week 6 baseline; those outcomes must be confirmed and documented during
Week 7.

## Week 7 Final Transition Outcome

### Handover Level
Ready for independent use

The customer confirmed that the provided documentation, deployment instructions, and repository are sufficient for the current transition scope.

### Customer Confirmation
Accepted with follow-up items

The customer reviewed the repository, Docker Compose deployment, runtime configuration, operational documentation, and product functionality.

The following follow-up items remain:

- Add a frontend switch between ML-based and rule-based detection.
- Complete the frontend interface for maintenance scripts.
- Continue improving the experimental ML subsystem.

These items do not prevent independent technical use of the product.

### Remaining Limitations
- The ML subsystem remains experimental.
- ML predictions depend on rule-based validation.
- Product behaviour depends on external exchange availability.
- Long-term production operation requires customer-managed infrastructure, secrets, backups, and monitoring.

### Final Public Artifacts
- Tickframe MVP v3 Release
- `reports/week7/README.md`
- `docs/customer-handover.md`
