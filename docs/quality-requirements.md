# Quality Requirements

This document defines maintained quality requirements for Tickframe using ISO/IEC 25010 sub-characteristics. Each requirement is written as a measurable scenario and is linked to automated quality requirement tests.

## Architecture Decision Traceability

| Quality requirement | Related architecture decisions |
|---|---|
| [QR-001: Market data update latency](#qr-001-market-data-update-latency) | [ADR-001: Independent exchange sources](architecture/adr/ADR-001-independent-exchange-sources.md), [ADR-002: TimescaleDB time-series storage](architecture/adr/ADR-002-timescaledb-time-series-storage.md), [ADR-003: WebSocket-driven market updates](architecture/adr/ADR-003-websocket-driven-market-updates.md), [ADR-004: Dockerized local deployment and observability](architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md) |
| [QR-002: Exchange data failure visibility](#qr-002-exchange-data-failure-visibility) | [ADR-001: Independent exchange sources](architecture/adr/ADR-001-independent-exchange-sources.md), [ADR-003: WebSocket-driven market updates](architecture/adr/ADR-003-websocket-driven-market-updates.md), [ADR-004: Dockerized local deployment and observability](architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md) |
| [QR-003: Critical module test coverage](#qr-003-critical-module-test-coverage) | [ADR-002: TimescaleDB time-series storage](architecture/adr/ADR-002-timescaledb-time-series-storage.md), [ADR-004: Dockerized local deployment and observability](architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md) |

## QR-001: Market data update latency

**ISO/IEC 25010 sub-characteristic:** Time behaviour

**Scenario:** When the market data provider sends a new OHLCV update under normal CI or production-like test conditions, the Tickframe backend shall process the update and make it available to the application within 1 second for at least 95% of tested updates.

**Why this matters:** Tickframe is a market analytics product. Users need recent market data so charts, metrics, and alerts remain useful during analysis.

**Traceability:** US-03, US-05, US-13, PB-08, PB-14

**Linked quality requirement tests:** [QRT-001](quality-requirement-tests.md#qrt-001-market-data-update-latency)

**Related architecture decisions:** [ADR-001](architecture/adr/ADR-001-independent-exchange-sources.md), [ADR-002](architecture/adr/ADR-002-timescaledb-time-series-storage.md), [ADR-003](architecture/adr/ADR-003-websocket-driven-market-updates.md), [ADR-004](architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md)

## QR-002: Exchange data failure visibility

**ISO/IEC 25010 sub-characteristic:** Fault tolerance

**Scenario:** When an exchange data source becomes unavailable under normal operation, the Tickframe application shall keep the UI usable and display the stale or disconnected data status within 10 seconds.

**Why this matters:** Exchange and network failures are realistic risks for a crypto market analytics product. Users need to know when data may be stale instead of trusting outdated analytics.

**Traceability:** US-10, PB-10

**Linked quality requirement tests:** [QRT-002](quality-requirement-tests.md#qrt-002-exchange-data-failure-visibility)

**Related architecture decisions:** [ADR-001](architecture/adr/ADR-001-independent-exchange-sources.md), [ADR-003](architecture/adr/ADR-003-websocket-driven-market-updates.md), [ADR-004](architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md)

## QR-003: Critical module test coverage

**ISO/IEC 25010 sub-characteristic:** Testability

**Scenario:** When a developer changes a critical product module under the standard CI environment, the module shall have automated tests that achieve at least 30% line coverage for that module.

**Why this matters:** Tickframe relies on critical analytics and pattern-recognition logic. Automated coverage helps detect regressions before changes are merged.

**Traceability:** PB-11, PB-12, PB-13, PB-14, docs/testing.md

**Linked quality requirement tests:** [QRT-003](quality-requirement-tests.md#qrt-003-critical-module-test-coverage)

**Related architecture decisions:** [ADR-002](architecture/adr/ADR-002-timescaledb-time-series-storage.md), [ADR-004](architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md)
