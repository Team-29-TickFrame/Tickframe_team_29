# ADR-001: Independent Exchange Sources

**Stable ID:** ADR-001

## Status

Accepted

## Context

Tickframe compares live and historical Spot market behavior across Binance and
Bybit. The product needs users to understand which exchange produced each
trade, candle, metric, and chart update. Blending prices from multiple
exchanges into one synthetic stream would make latency, stale-data status,
metric interpretation, and customer review evidence harder to inspect.

The current product also has exchange-specific failure modes. A WebSocket
endpoint may be blocked, slow, disconnected, or missing an instrument while the
other exchange remains healthy. Users need this to be visible instead of hidden
behind an averaged market view.

## Decision

Tickframe keeps `exchange` as a first-class part of market identity across
configuration, ingestion, storage, APIs, and UI state. Binance and Bybit are
collected independently, normalized into a common trade and candle shape, and
shown through exchange-aware controls instead of merged into a single price.

Fallback endpoints may be configured within an exchange. Cross-exchange
substitution is not used to silently replace an exchange price. If a chart uses
another source as an explicit fallback, the response source must make that
visible to the caller.

## Consequences and Tradeoffs

- Exchange-specific latency and stale-data status remain visible to users and
  reviewers.
- Metrics can be explained as Binance metrics or Bybit metrics without hiding
  source differences.
- The UI needs exchange controls and the backend needs exchange-specific
  validation on REST and WebSocket requests.
- Cross-exchange comparisons require explicit product behavior rather than an
  implicit blended stream.
- The data model stores more keys than a single-market stream, but the result
  is easier to audit and test.

## Quality Requirements Addressed

- [QR-001: Market data update latency](../../quality-requirements.md#qr-001-market-data-update-latency)
  because latency is measured and interpreted per exchange stream.
- [QR-002: Exchange data failure visibility](../../quality-requirements.md#qr-002-exchange-data-failure-visibility)
  because exchange-specific failures stay visible instead of being masked by
  another source.

## Related Implementation

- [`backend/config/markets.yaml`](../../../backend/config/markets.yaml)
- [`backend/app/config.py`](../../../backend/app/config.py)
- [`backend/app/exchanges/`](../../../backend/app/exchanges/)
- [`backend/app/store.py`](../../../backend/app/store.py)
- [`frontend/src/api.ts`](../../../frontend/src/api.ts)
