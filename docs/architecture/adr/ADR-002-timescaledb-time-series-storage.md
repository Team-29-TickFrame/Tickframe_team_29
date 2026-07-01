# ADR-002: TimescaleDB Time-Series Storage

**Stable ID:** ADR-002

## Status

Accepted

## Context

Tickframe needs recent live data, historical chart windows, metric history, and
reviewable evidence for real-time analytics. The product stores high-volume
raw trades, revision-aware `1s` candles, larger timeframe rollups, and metric
snapshots. A generic in-memory store is not enough because users scroll through
history, local downtime can create gaps, and CI or release evidence needs a
repeatable persistence model.

The storage layer also needs bounded growth. Raw trades are useful for short
timeframe repair, but retaining them forever would increase local deployment
cost and make the student team workflow harder to run.

## Decision

Tickframe uses TimescaleDB as the primary persistent store for market time
series. The backend writes raw trades, candle revisions, continuous or runtime
rollups, metric points, metric events, and latest metric summaries through the
database writer. The product keeps retention bounded: raw trades support short
repair windows, `1s` candles support recent detailed charts, and larger
timeframes support longer analysis.

The live in-memory store remains as a resilience layer for the dashboard. When
database history is unavailable, the backend can still serve recent in-memory
data and expose degraded health instead of failing the whole UI.

## Consequences and Tradeoffs

- Time-window queries, rollups, and retention match the market-data domain.
- The backend can rebuild short timeframe candles from retained raw trades
  when late messages or downtime affect recent history.
- Local setup needs PostgreSQL/TimescaleDB, so Docker Compose becomes part of
  the normal development and review workflow.
- Tests need to separate pure domain logic from database integration so the CI
  suite stays fast and reliable.
- Database health becomes an operational concern that must be visible through
  health and observability endpoints.

## Quality Requirements Addressed

- [QR-001: Market data update latency](../../quality-requirements.md#qr-001-market-data-update-latency)
  because storage, rollups, and recovery affect how quickly usable market data
  reaches API and chart consumers.
- [QR-003: Critical module test coverage](../../quality-requirements.md#qr-003-critical-module-test-coverage)
  because aggregation, history, database conversion helpers, and metrics are
  critical modules with maintained tests and coverage gates.

## Related Implementation

- [`backend/app/database.py`](../../../backend/app/database.py)
- [`backend/app/history.py`](../../../backend/app/history.py)
- [`backend/app/aggregation.py`](../../../backend/app/aggregation.py)
- [`backend/app/service.py`](../../../backend/app/service.py)
- [`docker-compose.yml`](../../../docker-compose.yml)
