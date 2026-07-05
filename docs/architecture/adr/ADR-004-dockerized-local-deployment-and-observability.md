# ADR-004: Dockerized Local Deployment and Observability

**Stable ID:** ADR-004

## Status

Accepted

## Context

Tickframe is no longer a static prototype. The maintained product needs a
backend collector service, a React frontend, TimescaleDB, Prometheus, and
Grafana. Reviewers and team members need a reproducible way to run the complete
stack without manually wiring service ports, database credentials, and
observability configuration.

The product also needs operational evidence for latency, freshness, collector
state, queue health, and display telemetry. These signals support Sprint review
discussion, quality requirements, and Definition of Done checks.

## Decision

Tickframe uses Docker Compose as the maintained local and deployment-oriented
runtime wrapper. The Compose stack starts TimescaleDB, backend, frontend,
Prometheus, and Grafana with health checks and persistent volumes where needed.
Runtime secrets are read from local environment files and are not committed.

The backend exposes health and Prometheus metrics. Prometheus scrapes backend
metrics, and Grafana is provisioned with the Tickframe latency dashboard so
reviewers can inspect exchange-to-backend latency, browser display latency,
market freshness, metric compute time, collector state, and queue behavior.

## Consequences and Tradeoffs

- The full product can be started through one documented workflow for local
  review and release evidence.
- Observability becomes part of the normal architecture instead of an optional
  screenshot-only activity.
- The local stack requires Docker and enough resources for five services.
- Secrets and public/private evidence must stay separated because Compose uses
  environment files for real credentials.
- CI still needs lightweight checks for code and docs because full exchange
  connectivity is environment-dependent.

## Quality Requirements Addressed

- [QR-001: Market data update latency](../../quality-requirements.md#qr-001-market-data-update-latency)
  because latency metrics and Grafana panels provide runtime evidence for the
  market update path.
- [QR-002: Exchange data failure visibility](../../quality-requirements.md#qr-002-exchange-data-failure-visibility)
  because health, freshness, collector, and queue signals expose degraded data
  paths.
- [QR-003: Critical module test coverage](../../quality-requirements.md#qr-003-critical-module-test-coverage)
  because the delivery workflow keeps CI, coverage gates, and local runtime
  verification aligned with the maintained architecture.

## Related Implementation

- [`docker-compose.yml`](../../../docker-compose.yml)
- [`observability/prometheus/prometheus.yml`](../../../observability/prometheus/prometheus.yml)
- [`observability/grafana/dashboards/tickframe-latency.json`](../../../observability/grafana/dashboards/tickframe-latency.json)
- [`backend/app/observability.py`](../../../backend/app/observability.py)
- [`docs/development-process.md`](../../development-process.md)
