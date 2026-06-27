# Issue #93 Latency Observability Evidence

Date: 2026-06-27

## Implemented Scope

- Added backend latency observability with rolling histograms and recent p50,
  p95, and p99 values for live market-data stages.
- Exported Prometheus metrics at `/metrics` and a JSON inspection snapshot at
  `/api/v1/observability/latency`.
- Added frontend display telemetry for market prices, stable candles,
  provisional candles, live metrics, and 24h statistics.
- Added Prometheus and Grafana services to `docker-compose.yml`.
- Provisioned a Grafana datasource and the `Tickframe Latency and Market
  Observability` dashboard.
- Kept Binance and Bybit as separate sources across all labels and panels.

## Measured Paths

| Stage | Meaning |
| --- | --- |
| `exchange_to_backend` | Exchange trade timestamp to backend WebSocket receive |
| `backend_queue` | Backend receive to trade consumer processing |
| `backend_to_frontend` | Backend snapshot generation to browser receive |
| `frontend_render` | Browser receive to post-render telemetry sample |
| `backend_to_display` | Backend receive to visible browser display |
| `exchange_to_display` | Exchange trade timestamp to visible browser display |
| `data_to_display` | Candle or metrics data timestamp to visible browser display |
| `backend_compute` | Backend metric calculation duration |
| `data_freshness` | Chart or metrics data lag at backend snapshot generation |

## Demo Links

- Grafana dashboard:
  <http://127.0.0.1:3000/d/tickframe-latency/tickframe-latency>
- Prometheus:
  <http://127.0.0.1:9090>
- Backend Prometheus metrics:
  <http://127.0.0.1:8000/metrics>
- Backend latency JSON:
  <http://127.0.0.1:8000/api/v1/observability/latency>

## Limitations

- Exchange timestamps are provided by Binance and Bybit and may have different
  precision or clock behavior.
- End-to-end browser display latency depends on the user's browser clock; local
  Docker demos share one host clock, while deployed systems should use NTP and
  mention possible browser clock skew.
- Prometheus stores the long-running time series. Backend rolling p50/p95/p99
  values reset when the backend process restarts.
- Frontend telemetry is throttled to avoid creating load from every rendered
  tick, so the dashboard shows sampled display latency rather than every frame.

## Verification

- `python3 -m unittest backend.tests.test_observability`
- `python3 -m unittest discover -s backend/tests`
- `npm run build`
- `docker compose config`
