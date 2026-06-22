# Tickframe Agent Context

This file is a working memory map for Codex. It is not a course deliverable and
should be updated whenever the project structure, run commands, architecture, or
important technical decisions change.

## Product Summary

Tickframe is a Dockerized real-time crypto market data and analytics product.
It collects public Spot market data from Binance and Bybit, normalizes trades,
builds OHLCV candles, stores data in TimescaleDB, computes metrics/pattern
events, and renders a React/TypeScript market terminal.

Current agreed instruments:

- BTC, ETH, SOL, XRP, AVAX, TON, TRX, BONK, PENGU, FLOKI against USDT.

Important product rule:

- Binance and Bybit are independent sources. Do not blend them into one
  synthetic price/candle.
- No trading, no API keys, no private user exchange data.

## Repository Map

- `backend/`: FastAPI backend, collectors, aggregation, DB, migrations, tests.
- `frontend/`: React + TypeScript + Vite terminal UI.
- `backend/config/markets.yaml`: canonical exchange endpoints and instrument
  symbol mapping.
- `backend/app/exchanges/`: live WebSocket collectors.
- `backend/app/aggregation.py`: 1s candle construction, late trade revisions,
  gap handling.
- `backend/app/database.py`: TimescaleDB writes, raw-trade chart rollups, and
  historical candle queries.
- `backend/app/history.py`: timeframe/range helpers and memory rollups.
- `backend/app/metrics.py`: metrics and pattern/metric events.
- `backend/scripts/backfill_candles.py`: serial REST OHLCV backfill into
  `historical_candles`; backend recovery currently imports helpers from this
  module.
- `backend/scripts/history.py`: faster manual parallel REST OHLCV backfill with
  per-exchange concurrency controls.
- `frontend/src/App.tsx`: app state, API polling, auth screen, dashboard.
- `frontend/src/components/MarketChart.tsx`: Lightweight Charts integration.
- `frontend/src/api.ts` and `frontend/src/types.ts`: frontend API boundary.
- `docs/`: assignment/process docs.
- `reports/week2`, `reports/week3`: Moodle/report artifacts.
- `swp_26/`: course assignments and requirements.

## Runtime Architecture

Docker Compose services:

- `timescaledb`: TimescaleDB/Postgres with persistent volume
  `tickframe-timescale-data`.
- `backend`: FastAPI, exchange collectors, TimescaleDB writer, recovery
  backfill.
- `frontend`: Nginx serving built Vite app and proxying API/WebSocket calls.

Main local URLs:

- Frontend: `http://127.0.0.1:4173`
- Backend docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Run And Verify

Typical Docker run:

```bash
docker compose up -d --build
```

After changing `.env`, force recreate affected containers:

```bash
docker compose up -d --build --force-recreate backend frontend
```

Useful local checks:

```bash
.venv/bin/python -m unittest discover -s backend/tests
cd frontend && npm run typecheck
cd frontend && npm run build
git diff --check
```

Useful API checks:

```bash
curl -sS --max-time 10 http://127.0.0.1:8000/health
curl -sS --max-time 10 'http://127.0.0.1:8000/api/v1/markets?exchange=bybit'
curl -sS --max-time 10 'http://127.0.0.1:8000/api/v1/candles?exchange=binance&instrumentId=BTC-USDT&timeframe=1m&limit=100'
```

Manual historical fill:

```bash
docker compose exec backend python -m backend.scripts.history --days 30
```

Use `--binance-concurrency`, `--bybit-concurrency`, `--request-sleep`, and
`--allow-failures` as needed. Without `--allow-failures`, `history.py` exits
non-zero if any selected market fails.

## Important Env Notes

`.env` is not committed. `.env.example` documents safe defaults.

Backend env must be explicitly passed through `docker-compose.yml`. Compose
using a variable for interpolation does not automatically expose that variable
inside the container.

Important variables:

- `POSTGRES_PASSWORD`
- `TICKFRAME_BINANCE_WS_URLS`
- `TICKFRAME_BYBIT_WS_URLS`
- `TICKFRAME_BINANCE_REST_URLS`
- `TICKFRAME_BYBIT_REST_URLS`
- `TICKFRAME_RECOVERY_BACKFILL_HOURS`
- `TICKFRAME_DISABLE_RECOVERY_BACKFILL`
- `TICKFRAME_BINANCE_1S_BACKFILL_HOURS`
- `TICKFRAME_SECOND_REPAIR_HOURS`
- `TICKFRAME_STABLE_CHART_DELAY_MS`

`TICKFRAME_RECOVERY_BACKFILL_HOURS` accepts formats like `72`, `72h`, `12d`,
and `12 days`.

`TICKFRAME_STABLE_CHART_DELAY_MS` defaults to `10000`. It also accepts strings
like `10s` and controls how far behind real time short chart candles are built.

`TICKFRAME_SECOND_REPAIR_HOURS` defaults to the recovery lookback and is capped
by `raw_trade_retention_hours`. It controls how much retained raw trade history
is used to repair stored `1s` candle rows after startup/reconnect.

`TICKFRAME_BINANCE_1S_BACKFILL_HOURS` controls automatic official Binance `1s`
REST kline import during recovery. These rows are stored in `historical_candles`.

If backend fails after recreating containers, check logs first. A common cause
is a mismatch between `.env` `POSTGRES_PASSWORD` and the password stored inside
the existing Timescale volume.

## Data And Recovery Decisions

Live collectors ingest public trades and build live `1s` candles only while the
backend is running. Short chart endpoints (`1s`, `5s`, `15s`) now prefer a
delayed TimescaleDB rollup directly from `raw_trades` so late WebSocket trades
are included before the candle is displayed.

Stored `1s` candles are also repaired from retained `raw_trades` during
recovery. This updates old missing/incomplete/too-early finalized seconds when
actual trades are available in the raw table.

Binance Spot REST supports `interval=1s`; Bybit Spot REST kline does not. For
Bybit second charts, the backend uses local live-trade seconds when present and
can fall back to Binance `1s` historical rows with source `binance_proxy_1s`.

REST recovery/backfill imports public `1m` OHLCV into `historical_candles`.
This can repair chart holes for `1m`, `5m`, `15m`, and `1h` after local
downtime. It cannot reconstruct exact missed `1s`, `5s`, or `15s` trades
because exchange WebSocket trades are not replayed after the backend was off.

Current recovery behavior:

- Recovery starts after backend startup.
- Recovery also starts after exchange reconnect.
- Default lookback is 72 hours unless overridden.
- `/health` exposes `recovery.running`, `lookbackHours`, `failedMarkets`, and
  progress fields.
- Recovery fills public `1m` REST history; it does not create exact missing
  second-level trade history for periods when the backend was fully offline.
- `/health.recovery.repairedSecondCandles` shows how many `1s` rows were
  repaired in the latest recovery run.
- `/health.recovery.insertedHistoricalSecondCandles` shows how many Binance
  official `1s` historical rows were imported in the latest recovery run.

Frontend chart behavior:

- `MarketChart` uses Lightweight Charts.
- `App.tsx` converts API candles to display candles.
- API `source` may now be `raw_trades`, `historical_candles`,
  `binance_proxy_1s`, `timescaledb`, or `memory`.
- Recent `1s`, `5s`, and `15s` chart windows are intentionally delayed by
  `TICKFRAME_STABLE_CHART_DELAY_MS` and rebuilt from `raw_trades`.
- During gaps/incomplete/null candles, the frontend may visually bridge with a
  flat zero-volume candle at the previous close while backend recovery catches
  up.

## Exchange Notes

Binance WebSocket defaults:

- `wss://data-stream.binance.vision/stream`
- fallback to `wss://stream.binance.com:9443/stream`
- fallback to `wss://stream.binance.com:443/stream`

Bybit WebSocket defaults include primary and regional/fallback hosts.

Bybit Spot rejects `publicTrade.TONUSDT`. Keep TON in the product because
Binance supports it, but treat Bybit TON as unsupported/rejected. The Bybit
collector subscribes one topic at a time so one rejected symbol does not break
all Bybit data.

## Git/Workspace Notes

The workspace is often dirty and has many untracked files. Do not revert or
delete user changes unless explicitly asked.

Known non-current legacy/static files may appear as deleted or untracked in git
status because the project evolved from static MVP to Dockerized full product.
Always inspect before cleanup.

## Update Protocol For This File

Update this file when:

- a new major directory/file role appears;
- Docker/env/run commands change;
- API contracts change;
- exchange/recovery behavior changes;
- a bug creates a lesson that future Codex should remember.

Do not put secrets, tokens, passwords, or private deployment credentials here.
