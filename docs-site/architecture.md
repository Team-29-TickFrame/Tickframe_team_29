# Architecture

Tickframe keeps the market-data path explicit from exchange collection through
chart display. The architecture documentation links current components to ADRs
and quality requirements.

## Runtime Flow

```text
Binance / Bybit public Spot streams
  -> backend exchange collectors
  -> canonical trades
  -> delayed and revision-aware OHLCV candles
  -> TimescaleDB raw trades, candle history, rollups, and metrics
  -> FastAPI REST and WebSocket endpoints
  -> React terminal, chart, metrics, and telemetry
  -> Prometheus and Grafana observability
```

## Architecture Decisions

| ADR | Decision |
|---|---|
| [ADR-001](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/architecture/adr/ADR-001-independent-exchange-sources.md) | Keep Binance and Bybit as independent sources. |
| [ADR-002](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/architecture/adr/ADR-002-timescaledb-time-series-storage.md) | Use TimescaleDB for market time-series storage. |
| [ADR-003](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/architecture/adr/ADR-003-websocket-driven-market-updates.md) | Use WebSockets for live market, candle, and metrics updates. |
| [ADR-004](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/architecture/adr/ADR-004-dockerized-local-deployment-and-observability.md) | Use Docker Compose plus Prometheus/Grafana for the maintained runtime and observability model. |

## Key Source Documents

- [Architecture README](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/architecture/README.md)
- [Backend service](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/backend/app/service.py)
- [Database writer](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/backend/app/database.py)
- [Frontend API bindings](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/frontend/src/api.ts)
