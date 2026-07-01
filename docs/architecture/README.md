# Tickframe Architecture

This page is the maintained architecture landing page for Tickframe. It links
the current architecture decisions to the product structure, quality
requirements, and Sprint 3 / Assignment 5 documentation.

## Current Architecture

Tickframe is a real-time crypto market analytics product. The product keeps
Binance and Bybit as independent market data sources, normalizes public Spot
trades, builds reproducible candles, stores history in TimescaleDB, and exposes
market data to a React terminal through REST and WebSocket APIs.

The main runtime flow is:

1. Exchange collectors in [`backend/app/service.py`](../../backend/app/service.py)
   and [`backend/app/exchanges/`](../../backend/app/exchanges/) subscribe to
   public Binance and Bybit Spot streams.
2. Exchange-specific messages are normalized into canonical trades using the
   configured market and instrument map in
   [`backend/config/markets.yaml`](../../backend/config/markets.yaml).
3. [`backend/app/aggregation.py`](../../backend/app/aggregation.py) converts
   trades into delayed, revision-aware `1s` OHLCV candles.
4. [`backend/app/database.py`](../../backend/app/database.py) persists raw
   trades, candle revisions, rollups, metric points, metric events, and latest
   metric summaries in TimescaleDB.
5. [`backend/app/main.py`](../../backend/app/main.py) exposes REST endpoints
   for initial reads and WebSocket endpoints for market, candle, and metric
   updates.
6. [`frontend/src/api.ts`](../../frontend/src/api.ts) and
   [`frontend/src/components/MarketChart.tsx`](../../frontend/src/components/MarketChart.tsx)
   render the terminal view with exchange, instrument, timeframe, chart,
   metric, and telemetry flows.
7. [`docker-compose.yml`](../../docker-compose.yml) runs the local product
   stack with backend, frontend, TimescaleDB, Prometheus, and Grafana.

## Decision Map

| Architecture concern | Decision record | Quality requirements |
|---|---|---|
| Keep exchange data inspectable and avoid synthetic blended prices. | [ADR-001: Independent exchange sources](adr/ADR-001-independent-exchange-sources.md) | [QR-001](../quality-requirements.md#qr-001-market-data-update-latency), [QR-002](../quality-requirements.md#qr-002-exchange-data-failure-visibility) |
| Store market history as time-series data with bounded retention and rollups. | [ADR-002: TimescaleDB time-series storage](adr/ADR-002-timescaledb-time-series-storage.md) | [QR-001](../quality-requirements.md#qr-001-market-data-update-latency), [QR-003](../quality-requirements.md#qr-003-critical-module-test-coverage) |
| Use WebSockets for live market, candle, and metrics updates while keeping REST for initial loads. | [ADR-003: WebSocket-driven market updates](adr/ADR-003-websocket-driven-market-updates.md) | [QR-001](../quality-requirements.md#qr-001-market-data-update-latency), [QR-002](../quality-requirements.md#qr-002-exchange-data-failure-visibility) |
| Keep the complete product runnable through Docker Compose with observable services. | [ADR-004: Dockerized local deployment and observability](adr/ADR-004-dockerized-local-deployment-and-observability.md) | [QR-001](../quality-requirements.md#qr-001-market-data-update-latency), [QR-002](../quality-requirements.md#qr-002-exchange-data-failure-visibility), [QR-003](../quality-requirements.md#qr-003-critical-module-test-coverage) |

## Related Maintained Documents

- [Root README](../../README.md) for product scope, local run guidance, and
  deployment notes.
- [Development process](../development-process.md) for branch, PR, CI, and
  configuration-management workflow.
- [Quality requirements](../quality-requirements.md) and
  [quality requirement tests](../quality-requirement-tests.md) for ISO/IEC
  25010 traceability.
- [Testing status](../testing.md) for current automated tests, CI gates, and
  coverage evidence.
- [Definition of Done](../definition-of-done.md) for the delivery gates that
  apply to later MVP v2 work.
