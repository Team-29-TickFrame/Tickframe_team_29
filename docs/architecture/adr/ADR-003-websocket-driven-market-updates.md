# ADR-003: WebSocket-Driven Market Updates

**Stable ID:** ADR-003

## Status

Accepted

## Context

Tickframe is useful only when the chart, market table, and metrics remain close
to current exchange data. Polling REST endpoints for every live update would
increase latency, duplicate work, and make frontend freshness harder to reason
about. At the same time, REST endpoints are still needed for initial chart
loads, pagination, recovery after reconnects, and deterministic checks.

The product also has two candle needs. Stable candles should be delayed enough
to avoid showing incomplete OHLC data as final. Provisional live overlays
should still let users see the current forming candle near real time.

## Decision

Tickframe uses REST for initial loads and history windows, then uses WebSocket
streams for live market, stable candle, provisional candle, and metric updates.
The backend owns revision counters and sends updates only when data changes.
The frontend opens exchange/instrument/timeframe-specific streams and merges
them with already loaded REST history.

Stable candle streams apply the configured chart delay. Provisional candle
streams are explicitly marked as provisional and are not treated as canonical
history.

## Consequences and Tradeoffs

- Users receive live updates without repeated REST polling.
- The product can separate canonical stable candles from provisional current
  candle overlays.
- The frontend must handle reconnects, stream-specific URLs, and merge rules
  between historical and live data.
- Backend stream state and revision counters add complexity, but they keep
  updates deterministic and reduce duplicate payloads.
- Failure visibility must be maintained through market status and health data
  when a stream becomes stale or disconnected.

## Quality Requirements Addressed

- [QR-001: Market data update latency](../../quality-requirements.md#qr-001-market-data-update-latency)
  because event-driven streams are the primary path for timely market updates.
- [QR-002: Exchange data failure visibility](../../quality-requirements.md#qr-002-exchange-data-failure-visibility)
  because stream health and stale market status are visible through the live
  market snapshots consumed by the UI.

## Related Implementation

- [`backend/app/main.py`](../../../backend/app/main.py)
- [`backend/app/service.py`](../../../backend/app/service.py)
- [`backend/app/store.py`](../../../backend/app/store.py)
- [`frontend/src/api.ts`](../../../frontend/src/api.ts)
- [`frontend/src/components/MarketChart.tsx`](../../../frontend/src/components/MarketChart.tsx)
