# Tickframe Market Data Backend

The backend consumes public Spot trade streams from Binance and Bybit,
normalizes them, builds canonical `1s` OHLCV candles, and exposes live plus
historical market state through REST and WebSocket APIs. Public market streams
do not require API keys. The metrics layer computes deterministic, versioned
market measurements from the same candle history used by the chart.

## Initial market scope

The versioned configuration in [`config/markets.yaml`](config/markets.yaml)
contains ten instruments:

- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- AVAX/USDT
- TON/USDT
- TRX/USDT
- BONK/USDT
- PENGU/USDT
- FLOKI/USDT

Each exchange remains a separate source. Tickframe never merges Binance and
Bybit OHLCV into a synthetic candle.

## Data behavior

- Decimal price and quantity parsing avoids early floating-point rounding.
- UTC Unix-epoch boundaries define every `1s` candle.
- A ten-second watermark allows delayed trades to arrive before finalization.
- Duplicate trade IDs do not increase volume or trade count.
- A connected stream with no trades creates `complete_empty`.
- A disconnected interval creates `incomplete` candles with null OHLC instead
  of inventing prices from the previous close.
- A late trade creates a new `recovered` candle revision.
- Raw trades expire from TimescaleDB after 72 hours.
- `1s` candles are compressed after 6 hours and retained for 14 days.
- Continuous aggregates preserve `1m`, `5m`, `15m`, and `1h` history after the
  underlying `1s` chunks expire.
- Imported exchange REST candles live in `historical_candles`, which has
  compression but no retention policy.
- Recent `1s`, `5s`, and `15s` chart windows are delayed and rebuilt directly
  from `raw_trades` for more accurate short-timeframe OHLC.
- Official Binance `1s` REST candles can be imported into `historical_candles`
  and are used for exact Binance second history.
- Bybit Spot REST does not expose historical `1s` klines; Bybit second charts
  use local live trades when available and can fall back to Binance `1s`
  historical candles as an explicit proxy source.
- Recovery also repairs stored `1s` candle rows from retained `raw_trades`
  after startup/reconnect, replacing stale incomplete rows when actual trades
  are available.
- `5m`, `15m`, and `1h` history can be derived from imported `1m` REST candles
  when the live `1s` source is outside its retention window.
- Final candles and their historical revisions remain reproducible while their
  source retention window is active.
- Metrics are calculated from returned candles, so API clients can reproduce
  every displayed value from the response window.

## Run with Docker

Create a local environment file:

```bash
cp .env.example .env
```

Replace the example `POSTGRES_PASSWORD` value, then run:

```bash
docker compose up --build
```

Open:

- Frontend: <http://127.0.0.1:4173>
- API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>
- Live markets: <http://127.0.0.1:8000/api/v1/markets>
- Client WebSocket: `ws://127.0.0.1:8000/ws/v1/markets`

## Run the backend without Docker

This mode keeps data in memory unless `DATABASE_URL` points to a migrated
TimescaleDB instance.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --reload --port 8000
```

## Tests

```bash
python3 -m unittest discover -s backend/tests
```

The critical tests cover exchange normalization, deduplication, event-time
ordering, UTC candle boundaries, empty seconds, late-trade revisions, exact
volume calculation, and OHLC invariants.

## API examples

Latest database-backed candles:

```text
GET /api/v1/candles?exchange=bybit&instrumentId=BTC-USDT&timeframe=1m&limit=300
```

Latest metrics for the same market:

```text
GET /api/v1/metrics?exchange=bybit&instrumentId=BTC-USDT&timeframe=1m&limit=300
```

Query an explicit half-open Unix-millisecond range:

```text
GET /api/v1/candles?exchange=binance&instrumentId=ETH-USDT&timeframe=5m&from=1781400000000&to=1781486400000&limit=1000
```

Filter the current market snapshot:

```text
GET /api/v1/markets?exchange=binance
```

Supported candle timeframes:

```text
1s, 5s, 15s, 1m, 5m, 15m, 1h
```

History responses include:

- `source`: `raw_trades`, `historical_candles`, `binance_proxy_1s`,
  `timescaledb`, or the limited `memory` fallback
- `hasMore`: whether an older page exists in the scanned range
- `nextBefore`: the earliest returned `openTime`, suitable as the next `to`
- `from` and `to`: the resolved half-open query range

The frontend automatically requests the next page when the chart approaches
its left edge.

Short chart timeframes (`1s`, `5s`, `15s`) use `raw_trades` with a stable
display delay. Configure the delay in `.env`:

```bash
TICKFRAME_STABLE_CHART_DELAY_MS=10000
# also accepted:
TICKFRAME_STABLE_CHART_DELAY_MS=10s
TICKFRAME_BINANCE_1S_BACKFILL_HOURS=24h
TICKFRAME_SECOND_REPAIR_HOURS=72h
```

Use a larger value, for example `15000` or `30000`, if a network frequently
delivers exchange trade messages late. Live last-trade prices still update
immediately; only the candle history endpoint waits before exposing the newest
short-timeframe bucket.

The stored `1s` repair window is controlled by `TICKFRAME_SECOND_REPAIR_HOURS`.
It is capped by the `raw_trade_retention_hours` setting because exact seconds
can only be rebuilt while the underlying public trades are still retained.

Official Binance `1s` historical import is controlled separately by
`TICKFRAME_BINANCE_1S_BACKFILL_HOURS`. Use the manual loader for deeper
backfills:

```bash
docker compose exec backend python -m backend.scripts.history --exchange binance --timeframe 1s --days 1
```

## Historical REST backfill

Load 30 days of public `1m` OHLCV for all configured instruments on Binance and
Bybit:

```bash
docker compose exec backend python -m backend.scripts.backfill_candles --days 30
```

For faster manual loading, use the parallel script:

```bash
docker compose exec backend python -m backend.scripts.history --days 30
```

Useful narrower runs:

```bash
docker compose exec backend python -m backend.scripts.backfill_candles --exchange binance --instrument BTC-USDT --days 1
docker compose exec backend python -m backend.scripts.backfill_candles --exchange bybit --instrument SOL --days 7
```

The script writes to `historical_candles` with `ON CONFLICT DO UPDATE`, so it is
safe to rerun. Binance REST candles include exchange trade counts; Bybit's Spot
kline endpoint does not expose trade counts, so imported Bybit candles store
`trade_count = 0` while preserving OHLCV.

Live collectors and REST backfill both support endpoint fallbacks. Defaults are
defined in `backend/config/markets.yaml`, and network-specific overrides can be
set in `.env`:

```bash
TICKFRAME_BINANCE_WS_URLS=wss://data-stream.binance.vision/stream,wss://stream.binance.com:9443/stream
TICKFRAME_BYBIT_WS_URLS=wss://stream.bybit.com/v5/public/spot,wss://stream.bybit-tr.com/v5/public/spot,wss://stream.bybit.kz/v5/public/spot
TICKFRAME_BINANCE_REST_URLS=https://data-api.binance.vision/api/v3/klines,https://api.binance.com/api/v3/klines
TICKFRAME_BYBIT_REST_URLS=https://api.bybit.kz/v5/market/kline,https://api.bybit.com/v5/market/kline,https://api.bytick.com/v5/market/kline
```

The backend also starts a small recovery backfill after startup or exchange
reconnection. It imports recent public `1m` OHLCV into `historical_candles`,
which lets `1m`, `5m`, `15m`, and `1h` chart windows recover from local
downtime without permanent holes. Defaults:

```bash
TICKFRAME_RECOVERY_BACKFILL_HOURS=72h
# or
TICKFRAME_RECOVERY_BACKFILL_HOURS=12d
TICKFRAME_DISABLE_RECOVERY_BACKFILL=0
TICKFRAME_BINANCE_1S_BACKFILL_HOURS=24h
TICKFRAME_SECOND_REPAIR_HOURS=72h
TICKFRAME_STABLE_CHART_DELAY_MS=10000
```

After changing `.env`, recreate the backend container so Docker passes the new
environment into Python:

```bash
docker compose up -d --build --force-recreate backend
```

Metrics responses include:

- `version`: current metrics calculation version, currently `metrics-v3`
- `windows`: rolling periods used by RSI, momentum, volatility estimators,
  mean reversion, price-volume divergence, and volume-spike calculations
- `latest`: the newest complete metric point in the response
- `points`: one metric point per returned candle
- `events`: deterministic metric events such as `volume_spike`,
  `volatility_shift`, `vwap_extension`, `rsi_extreme`,
  `mean_reversion_stretch`, `price_volume_divergence`, `double_top`,
  `double_bottom`, `bullish_rsi_divergence`, `bearish_rsi_divergence`,
  `bullish_price_volume_divergence`, and
  `bearish_price_volume_divergence`
- `crossPairCorrelations`: same-window return correlations against the other
  configured instruments on the selected exchange

Current metrics:

- VWAP and VWAP deviation over the returned window
- window realized volatility from rolling log returns
- Parkinson and Garman-Klass range volatility estimators
- simple rolling RSI
- short and long momentum versus configured lookbacks
- rolling mean-reversion z-score and distance from mean
- price-versus-volume divergence when price moves while volume contracts
- current volume divided by rolling baseline volume

Metric event `confidence` is a normalized rule-strength score. It is not a
prediction and it is not trading advice.

## Storage lifecycle

- `raw_trades`: 6-hour chunks, retained for 72 hours
- `candles`: 1-day chunks, compressed after 6 hours, retained for 14 days
- `historical_candles`: compressed after 7 days, no retention policy
- continuous aggregate refresh window: the newest 13 days only
- `1m`, `5m`, `15m`, `1h` aggregate history: no retention policy

The one-day gap between the aggregate refresh window and `1s` retention is
intentional. A continuous aggregate must not refresh over already deleted raw
chunks, otherwise TimescaleDB would also delete the corresponding rollup.

## Deployment

Shared static hosting cannot run this service. Deploy the Compose application
on a Linux VM or VPS with persistent storage, NTP synchronization, HTTPS/WSS
termination, backups, and monitoring.
