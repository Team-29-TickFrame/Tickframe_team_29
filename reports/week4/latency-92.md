# Issue #92 Latency Evidence

Date: 2026-06-26

## Delay Sources Identified

- Collector ingestion: exchange trade timestamps are compared with backend
  receive time and exposed as `latencyMs`; collector freshness is exposed as
  `messageAgeMs`.
- Backend candle finalization: `allowed_lateness_ms` delayed the in-memory
  candle watermark by 10000 ms before this change.
- Backend chart history: `TICKFRAME_STABLE_CHART_DELAY_MS` delayed recent
  `1s`, `5s`, and `15s` raw-trade chart windows by 10000 ms before this change.
- Frontend chart refresh: `1s` and `5s` charts polled every 2000 ms, while
  `15s` charts polled every 5000 ms before this change.
- Backend WebSocket delivery: market, provisional candle, and metrics streams
  used short sleep loops before the event-driven update path.
- Frontend chart rendering: every refresh called `setData` for the complete
  candle and volume arrays before this change.

## Changes Made

- Reduced the default short-chart stable delay from 10000 ms to 2000 ms.
- Reduced the configured candle watermark from 10000 ms to 2000 ms.
- Replaced chart-tail polling with `/ws/v1/candles/stable`, an event-driven
  stable candle stream built from the finalized in-memory candle window.
- Added `chartLatency` diagnostics to candle responses so the UI can show the
  actual returned data lag.
- Added chart footer labels for `chart lag` and `late window`.
- Switched normal tail refreshes in `MarketChart` to incremental series updates;
  full `setData` is still used for scope changes, prepended history, or older
  revisions.
- Added persisted backend-owned metric history:
  `metric_points`, `metric_events`, and `metric_summaries`.
- Added a coalesced metrics worker that recomputes affected metric windows when
  new or recovered candles arrive.
- Added `/ws/v1/metrics` so fresh metric summaries can be pushed to the
  frontend instead of waiting for the fallback polling interval.
- Cached cross-pair correlations for 60000 ms so the heaviest peer-comparison
  work runs at most once per minute per active metric scope.
- Added `/ws/v1/candles` for provisional live candle overlays, keeping stable
  history delayed for correctness while showing the current forming candle
  almost immediately.
- Converted market, provisional candle, stable candle, and metric WebSocket
  delivery to backend event notifications instead of fixed sleep-loop polling.
- Added `/health.streams` revision counters for market, provisional candle,
  stable candle, and metrics stream progress.

## Before / After Budget

| Path | Before | After |
| --- | ---: | ---: |
| Candle watermark | 10000 ms | 2000 ms |
| Stable short-chart delay | 10000 ms | 2000 ms |
| `1s` / `5s` chart tail refresh | 2000 ms polling | event-driven stable WS |
| `15s` chart tail refresh | 5000 ms polling | event-driven stable WS |
| Metrics delivery | REST polling only | event-driven WebSocket push + REST fallback |
| Cross-pair correlations | every metrics response | cached for 60000 ms |
| Current candle display | stable polling only | provisional WebSocket overlay |
| Market/provisional WS wakeup | fixed 100 ms loop | event notification |
| Metrics WS wakeup | fixed 250 ms loop | event notification |

Expected visible lag for `1s` charts drops from roughly 10-13 seconds
(`10000 ms` stable delay plus bucket alignment and polling) to roughly
2.0-2.2 seconds for stable candles (`2000 ms` stable delay plus backend
finalizer/event overhead, without frontend tail polling).
The current forming candle is now also streamed as a provisional overlay, so
users can see live candle movement near the trade stream cadence while waiting
for the corrected stable candle.

Late exchange messages are not hidden: existing recovered candle revisions are
still preserved, and the UI now exposes the current chart lag rather than
presenting delayed candles as fully live.

Metric history is now kept as canonical rows per candle and metrics version.
Recovered candles trigger affected metric-window recomputation and upserts,
which keeps latest dashboards fresh while preserving a queryable metric history
for future analysis and backtests.

## Verification

- `.venv/bin/python -m unittest discover -s backend/tests`
- `npm run build`
