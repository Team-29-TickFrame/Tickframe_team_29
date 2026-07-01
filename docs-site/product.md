# Product

Tickframe is a real-time crypto market data and pattern-analysis product. The
current product collects public Binance and Bybit Spot trades, normalizes them,
builds reproducible `1s` OHLCV candles, stores history in TimescaleDB, and
exposes the result in a React terminal with deterministic market metrics.

## Maintained Scope

- Binance and Bybit remain independent exchange sources.
- The UI does not blend exchanges into synthetic prices or candles.
- Supported instruments are the maintained USDT markets listed in the product
  configuration.
- The backend exposes REST history endpoints and live WebSocket streams.
- Metrics include VWAP, volatility estimators, RSI, momentum, mean reversion,
  divergences, anomalies, and cross-pair correlations.
- The deployment model uses Docker Compose with backend, frontend, TimescaleDB,
  Prometheus, and Grafana.

## Key Source Documents

- [Root README](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/README.md)
- [Roadmap](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/roadmap.md)
- [User stories](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/user-stories.md)
- [Docker Compose runtime](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docker-compose.yml)
