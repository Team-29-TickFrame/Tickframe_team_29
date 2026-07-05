## Static View - Component Diagram
show parts of the product and the simple "uses" relationships
between them.

### What The Static View Shows

The static view shows Tickframe as three main areas:

1. The user works with the React frontend.
2. The frontend asks the FastAPI backend for data through REST and WebSocket
   connections.
3. The backend coordinates exchange collectors, candle building, live state,
   metrics, ML pattern lookup, database persistence, and monitoring.

Outside the backend, Tickframe depends on Binance and Bybit for public market
data, TimescaleDB for stored trades/candles/metrics, model files for the ML
pattern endpoint, and Prometheus/Grafana for observability.

### Coupling And Cohesion

The design is cohesive because each major component has a clear job. Exchange
collectors talk to Binance and Bybit. `CandleAggregator` builds candles.
`LiveStore` keeps the latest in-memory market state. The metrics engine
computes analytics. `DatabaseWriter` handles persistence. The frontend mostly
renders data and sends requests through `frontend/src/api.ts`.

The main coupling risk is `MarketDataService`. It is the central coordinator
for many backend tasks, so many arrows point to it. This is understandable for
the MVP because it makes the live-data flow easy to follow. Later, if the
product grows, collectors, metrics workers, and recovery/backfill jobs may need
to become more separate services.

### Maintainability Implications

The structure is maintainable enough for the current product because most
changes have an obvious place. A new exchange parser belongs in the collectors.
A new metric belongs in the metrics engine. A new chart or alert control
belongs in the frontend. A storage change belongs near `DatabaseWriter` and
TimescaleDB.

The part to watch is the backend coordinator. When `MarketDataService` changes,
it can affect collectors, candles, metrics, streams, and storage at the same
time. That is why tests and quality gates around this path are important.

### Quality Requirements Supported Or Constrained

- [QR-001: Market data update latency](../quality-requirements.md#qr-001-market-data-update-latency)
  is supported by WebSocket streams, in-memory live state, queue-based trade
  processing, and explicit latency observability.
- [QR-002: Exchange data failure visibility](../quality-requirements.md#qr-002-exchange-data-failure-visibility)
  is supported by independent collectors and visible health/freshness state.
- [QR-003: Critical module test coverage](../quality-requirements.md#qr-003-critical-module-test-coverage)
  is supported by cohesive critical modules that can be tested separately.
- QR-001 is constrained by the single backend process and shared service
  orchestration. Under heavier load, workers or bounded background services may
  need to be separated.
- QR-003 is constrained by deployment and database paths that are harder to
  cover without integration fixtures.

## Dynamic View - Live Market Update Sequence

Sources:
[PlantUML](dynamic-view/live-market-update-sequence.puml) and
[Mermaid](dynamic-view/live-market-update-sequence.mmd).

The dynamic perspective documents one non-trivial runtime workflow involving
several components and multiple transactions.

### Scenario Represented

This dynamic view represents the non-trivial live market-data workflow from an
exchange trade event to visible UI updates and observability telemetry. The
flow includes external exchange APIs, exchange parsing, queueing, aggregation,
persistence, metric recomputation, WebSocket delivery, frontend display, and
display-latency reporting.

### Why This Scenario Matters

This scenario is central to Tickframe because the product value depends on
recent market information, clear chart state, and visible analytics. It is also
the flow most likely to expose architecture risks: slow processing, stale
exchange data, inconsistent candle state, database outages, or a mismatch
between backend update time and frontend display time.

### Boundaries, Decisions, And Quality Reasoning

The sequence explains why [ADR-001](adr/ADR-001-independent-exchange-sources.md)
keeps exchange sources independent, why [ADR-002](adr/ADR-002-timescaledb-time-series-storage.md)
stores raw trades and candle history as time-series data, and why
[ADR-003](adr/ADR-003-websocket-driven-market-updates.md) uses WebSockets for
live market, candle, and metrics updates. It also supports reasoning about
[QR-001](../quality-requirements.md#qr-001-market-data-update-latency) and
[QR-002](../quality-requirements.md#qr-002-exchange-data-failure-visibility)
because latency and freshness are captured along the same event path that users
see in the terminal.

## Deployment View - Docker Compose Runtime

Sources:
[PlantUML](deployment-view/docker-compose-deployment.puml) and
[Mermaid](deployment-view/docker-compose-deployment.mmd).

The deployment perspective is a high-level runtime view rather than one
scenario. 

### What The Deployment View Shows

The deployment view shows the maintained runtime model from
[`docker-compose.yml`](../../docker-compose.yml): a frontend container, backend
container, private TimescaleDB datastore, Prometheus, Grafana, persistent Docker
volumes, and private `.env` runtime configuration. The customer-facing path is
browser access through an optional host reverse proxy to the frontend, which
then calls the backend over REST and WebSocket routes.

### Why This Deployment Model Was Chosen

Docker Compose was chosen because Tickframe is not only a static frontend. The
product requires Python collectors, WebSocket services, a stateful time-series
database, and observability services. A single Compose stack gives the team and
reviewers one reproducible deployment shape for local runs and VM/VPS hosting,
while keeping secrets in `.env` and documenting safe defaults in
[`.env.example`](../../.env.example).

### Product Support And Constraints

This deployment supports MVP v2 by making the customer-facing terminal, API,
database, and observability stack runnable together. It also supports
[ADR-004](adr/ADR-004-dockerized-local-deployment-and-observability.md), which
keeps operational evidence inspectable through Prometheus and Grafana.

The model constrains the product because all application workers run inside one
backend service. That is acceptable for the current MVP, but production growth
may require separate collector, metric-worker, and API processes. The database
volume also needs backup and retention management when the product is operated
for a customer beyond grading or demo use.

### Deployment And Operation Considerations

- Keep `.env` private and submit any required access credentials only through
  Moodle or another approved private channel.
- Put a host-level reverse proxy in front of the frontend for public HTTPS/WSS
  access.
- Keep TimescaleDB private to the Compose network and persist it through the
  `tickframe-timescale-data` volume.
- Synchronize the host clock with NTP so latency measurements are meaningful.
- Monitor `/health`, `/metrics`, Prometheus, and Grafana before declaring a
  Sprint increment ready for customer review.

