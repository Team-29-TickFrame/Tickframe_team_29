# Tickframe

Tickframe is a real-time crypto market data and pattern-analysis product. The
current version collects public Binance and Bybit Spot trades, normalizes them,
builds reproducible `1s` OHLCV candles, stores them in TimescaleDB, and exposes
the result in a read-only React terminal with deterministic market metrics.

Binance and Bybit remain independent sources. The UI never blends them into a
synthetic price or candle.


## Current Scope

- 10 canonical USDT instruments: BTC, ETH, SOL, XRP, AVAX, GRAM, TRX, BONK,
  PENGU, FLOKI; exchange support is explicit per instrument
- Public Binance and Bybit WebSocket collectors
- Event-time `1s` OHLCV with gaps and late-trade revisions
- TimescaleDB history with stable delayed `1s`, `5s`, `15s` raw-trade
  rollups plus `1m`, `5m`, `15m`, and `1h`
- Automatic backward history loading on chart scroll
- Versioned metrics engine with VWAP, realized volatility, Parkinson and
  Garman-Klass estimators, RSI, momentum, mean reversion, divergences,
  statistical anomalies, cross-pair correlations, and deterministic metric
  events
- REST history plus a live market WebSocket
- Persisted metric history plus pushed metric snapshots for the terminal
- Prometheus latency metrics and a provisioned Grafana observability dashboard
- React and TypeScript terminal with exchange, instrument, and timeframe controls
- TimescaleDB persistence and Docker Compose deployment

Pattern detectors and chart-pattern confidence are already exposed through the
metrics layer, while the backtest harness is still planned next. The UI
deliberately separates metric events from trading advice and does not invent
buy/sell signals.

Storage is bounded: raw trades are retained for 72 hours, `1s` candles for 14
days, and older `1m`/`5m`/`15m`/`1h` continuous aggregates are kept for
long-term analysis. Exchange REST backfills are stored separately as imported
historical candles, so 30-day `1m` history is not deleted by the `1s` retention
policy. Old second candles are compressed automatically.

## Planning and workflow

- Current user-story index: [docs/user-stories.md](docs/user-stories.md)
- Current roadmap: [docs/roadmap.md](docs/roadmap.md)
- Hosted documentation site: <https://team-29-tickframe.github.io/Tickframe_team_29/>
- Definition of Done: [docs/definition-of-done.md](docs/definition-of-done.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Issue forms: [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE/)
- PR template: [.github/pull_request_template.md](.github/pull_request_template.md)
- Development process and configuration management: [docs/development-process.md](docs/development-process.md)

## Run the Complete Product

Create the local environment file and choose a real password:

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: <http://127.0.0.1:4173>
- API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>
- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000/d/tickframe-latency/tickframe-latency>

Useful API checks:

- Candles: <http://127.0.0.1:8000/api/v1/candles?exchange=binance&instrumentId=BTC-USDT&timeframe=1m&limit=100>
- Metrics: <http://127.0.0.1:8000/api/v1/metrics?exchange=binance&instrumentId=BTC-USDT&timeframe=1m&limit=300>
- Prometheus metrics: <http://127.0.0.1:8000/metrics>
- Latency snapshot: <http://127.0.0.1:8000/api/v1/observability/latency>
- Experimental ML pattern: <http://127.0.0.1:8000/api/v1/patterns/ml?exchange=binance&instrumentId=BTC-USDT&timeframe=1m>
- Metrics stream: `ws://127.0.0.1:8000/ws/v1/metrics?exchange=binance&instrumentId=BTC-USDT&timeframe=1m&window=24h`
- Stable candle stream: `ws://127.0.0.1:8000/ws/v1/candles/stable?exchange=binance&instrumentId=BTC-USDT&timeframe=1s&limit=20`
- Provisional candle stream: `ws://127.0.0.1:8000/ws/v1/candles?exchange=binance&instrumentId=BTC-USDT&timeframe=1s`

Load 30 days of public `1m` OHLCV for every configured instrument and exchange:

```bash
docker compose exec backend python -m backend.scripts.backfill_candles --days 30
```

Faster parallel loader:

```bash
docker compose exec backend python -m backend.scripts.history --days 30
```

The command is idempotent: reruns update the same candle keys instead of
duplicating rows.

Load official Binance `1s` historical candles for exact second charts:

```bash
docker compose exec backend python -m backend.scripts.history --exchange binance --timeframe 1s --days 1
```

Bybit Spot REST does not expose historical `1s` klines. Tickframe keeps Bybit
live seconds when our WebSocket captured trades, and can explicitly fall back
to Binance `1s` historical candles for gap-free second charts when Bybit
seconds are unavailable.

If an exchange endpoint is blocked or unstable on the current network, override
the comma-separated fallback list in `.env`:

```bash
TICKFRAME_BINANCE_WS_URLS=wss://data-stream.binance.vision/stream,wss://stream.binance.com:9443/stream
TICKFRAME_BYBIT_WS_URLS=wss://stream.bybit.com/v5/public/spot,wss://stream.bybit-tr.com/v5/public/spot,wss://stream.bybit.kz/v5/public/spot
TICKFRAME_BINANCE_REST_URLS=https://data-api.binance.vision/api/v3/klines,https://api.binance.com/api/v3/klines
TICKFRAME_BYBIT_REST_URLS=https://api.bybit.kz/v5/market/kline,https://api.bybit.com/v5/market/kline,https://api.bytick.com/v5/market/kline
TICKFRAME_BINANCE_1S_BACKFILL_HOURS=24h
TICKFRAME_SECOND_REPAIR_HOURS=72h
TICKFRAME_STABLE_CHART_DELAY_MS=2000
```

The maintained market config may omit an exchange symbol when that venue has no
active Spot market. For example, the canonical `GRAM-USDT` instrument currently
uses Bybit's `GRAMUSDT` Spot symbol and does not subscribe to Binance while
Binance reports the old `TONUSDT` market as unavailable.

After backend startup or exchange reconnection, Tickframe automatically
backfills recent public `1m` OHLCV into `historical_candles` so chart windows do
not keep permanent holes after local downtime. The default recovery window is
72 hours and can be changed with `TICKFRAME_RECOVERY_BACKFILL_HOURS`; accepted
examples are `72`, `72h`, or `12d`. After changing `.env`, recreate the backend
container with `docker compose up -d --build --force-recreate backend`.

Short chart timeframes (`1s`, `5s`, `15s`) are intentionally delayed by
`TICKFRAME_STABLE_CHART_DELAY_MS` and rebuilt from `raw_trades` instead of the
freshest finalized candle rows. The default is `2000` ms, aligned with the
default `allowed_lateness_ms` candle watermark. Late exchange messages can
still revise recent candles instead of being hidden.

During the same recovery run, Tickframe also repairs already stored `1s`
candles from retained `raw_trades`. `TICKFRAME_SECOND_REPAIR_HOURS` controls
the repair window and is capped by the raw-trade retention period. This can fix
past `1s` candle gaps when the trades were received but the candle row was
missing, incomplete, or finalized too early.

Tickframe also backfills recent official Binance `1s` REST candles on recovery;
`TICKFRAME_BINANCE_1S_BACKFILL_HOURS` controls that window. These rows are used
directly for Binance second charts and as an explicit `binance_proxy_1s` source
for Bybit second charts when exact Bybit seconds do not exist locally.

Metric points, metric events, and latest metric summaries are persisted in
TimescaleDB. The REST metrics endpoint remains available for initial loads and
fallbacks, while `/ws/v1/metrics` pushes fresh backend-owned summaries after
new or recovered candle windows are recomputed.

Latency observability is exported from the backend at `/metrics` for
Prometheus and at `/api/v1/observability/latency` as JSON. The Compose stack
provisions Grafana with a Tickframe dashboard that covers exchange-to-backend
latency, browser display latency, latest prices, trade freshness, metrics
compute time, collector state, and internal queues. Frontend display telemetry
is sent after the dashboard receives and renders market, candle, and metrics
updates, so the end-to-end series measure the path toward the user's screen
instead of only the backend receive time.

Display latency depends on browser and server clocks being reasonably aligned.
Local Docker runs share the host clock closely; public deployments should keep
the server synchronized with NTP and treat browser-clock skew as a measurement
limitation.

The chart loads its initial history through REST, then listens to
`/ws/v1/candles/stable` for event-driven stable candle updates and
`/ws/v1/candles` for provisional live overlays. Provisional overlays are not
persisted as canonical history; they let the user see the current forming candle
near real time while stable candles remain delayed enough to preserve OHLC
correctness.

Stop the stack with:

```bash
docker compose down
```

## Local Development

Run the backend in one terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --reload --port 8000
```

Run the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves <http://127.0.0.1:4173> and proxies `/api`, `/health`, and `/ws`
to the backend on port `8000`.

Useful checks:

```bash
cd frontend
npm run build

cd ..
python3 -m unittest discover -s backend/tests
```

## ML Training Pipeline

The first maintained pattern-recognition experiment lives in
[ml/pattern_recognition](ml/pattern_recognition). It trains a synthetic `1m`
baseline for 96-candle windows and saves reproducible model artifacts.

```bash
python -m ml.pattern_recognition.train_baseline --config ml/pattern_recognition/config.json
```

The training pipeline itself is offline. The saved baseline artifact is exposed
through the experimental `/api/v1/patterns/ml` endpoint and the dashboard ML
pattern panel for the `1m` timeframe only. Other timeframes remain unsupported
until separate training and validation artifacts exist for them.

## Deployment

The complete product needs a Linux VM or VPS. Shared static hosting cannot run
the Python collectors, WebSocket service, or TimescaleDB.

The historical MVP v0 remains available at <https://tickframe.h1n.ru/>. It is a
static prototype and does not represent the current live-data MVP v1 stack.
Public MVP v1 deployment and the `v1.0.0` release are tracked in
[PB-07](https://github.com/Team-29-TickFrame/Tickframe_team_29/issues/43).

On the server, install Docker, copy the repository, create `.env`, and run:

```bash
docker compose up -d --build
```

For public deployment, put a host-level reverse proxy in front of the Compose
frontend, terminate HTTPS/WSS there, keep TimescaleDB private, enable persistent
backups, and synchronize the host clock with NTP.

## Project Notes

- Backend details: [backend/README.md](backend/README.md)
- Pattern ML pipeline: [ml/pattern_recognition/README.md](ml/pattern_recognition/README.md)
- Week 2 submission index: [reports/week2/README.md](reports/week2/README.md)
- Week 3 submission index: [reports/week3/README.md](reports/week3/README.md)
- MVP v0 report: [reports/week2/mvp-v0-report.md](reports/week2/mvp-v0-report.md)

Never commit real `.env` files, passwords, or API credentials.
