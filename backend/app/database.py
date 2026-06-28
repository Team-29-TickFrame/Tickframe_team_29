import asyncio
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .history import (
    HistoryPage,
    PERSISTED_TIMEFRAMES,
    RUNTIME_TIMEFRAMES,
    TIMEFRAME_SECONDS,
    timeframe_ms,
)
from .models import Candle, Trade


DatabaseEvent = Tuple[str, object]
ROLLUP_VIEWS = {
    "1m": "candles_1m",
    "5m": "candles_5m",
    "15m": "candles_15m",
    "1h": "candles_1h",
}
SQL_INTERVALS = {
    "5s": "5 seconds",
    "15s": "15 seconds",
}


class DatabaseWriter:
    def __init__(
        self,
        database_url: Optional[str] = None,
        queue_size: int = 200_000,
        batch_size: int = 1000,
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.batch_size = batch_size
        self.queue: "asyncio.Queue[DatabaseEvent]" = asyncio.Queue(maxsize=queue_size)
        self.engine: Optional[AsyncEngine] = None
        self.connected = False
        self.last_error: Optional[str] = None
        self.written_trades = 0
        self.written_candles = 0
        self.written_metric_points = 0
        self.written_metric_events = 0
        self.written_metric_summaries = 0
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if not self.database_url:
            return
        self.engine = create_async_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        self.connected = True
        self._task = asyncio.create_task(self._run(), name="database-writer")

    async def stop(self) -> None:
        if self._task is not None:
            await self.queue.join()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.engine is not None:
            await self.engine.dispose()
        self.connected = False

    async def enqueue_trade(self, trade: Trade) -> None:
        if self.engine is not None:
            await self.queue.put(("trade", trade))

    async def enqueue_candle(self, candle: Candle) -> None:
        if self.engine is not None:
            await self.queue.put(("candle", candle))

    async def enqueue_metrics(self, payload: Dict[str, Any]) -> None:
        if self.engine is not None:
            await self.queue.put(("metrics", payload))

    async def candle_history(
        self,
        *,
        exchange: str,
        market_type: str,
        instrument_id: str,
        timeframe: str,
        from_ms: int,
        to_ms: int,
        limit: int,
    ) -> Optional[HistoryPage]:
        if self.engine is None:
            return None

        if timeframe == "1s":
            statement = self._one_second_history_sql()
        elif timeframe in RUNTIME_TIMEFRAMES:
            statement = self._runtime_rollup_sql(timeframe)
        elif timeframe in PERSISTED_TIMEFRAMES:
            statement = self._persisted_rollup_sql(timeframe)
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        params = {
            "exchange": exchange,
            "market_type": market_type,
            "instrument_id": instrument_id,
            "from_ms": from_ms,
            "to_ms": to_ms,
            "fetch_limit": limit + 1,
            "source_fetch_limit": ((limit + 2) * TIMEFRAME_SECONDS[timeframe]),
        }
        try:
            async with self.engine.connect() as connection:
                result = await connection.execute(text(statement), params)
                rows = list(result.mappings().all())
            self.connected = True
            self.last_error = None
        except Exception as error:
            self.connected = False
            self.last_error = str(error)
            raise

        has_more = len(rows) > limit
        rows.reverse()
        if has_more:
            rows = rows[1:]

        history_source = self._history_page_source(rows)
        return HistoryPage(
            candles=[self._history_row_to_api(row, timeframe) for row in rows],
            has_more=has_more,
            source=history_source,
        )

    async def raw_trade_candle_history(
        self,
        *,
        exchange: str,
        market_type: str,
        instrument_id: str,
        timeframe: str,
        from_ms: int,
        to_ms: int,
        limit: int,
    ) -> Optional[HistoryPage]:
        if self.engine is None:
            return None
        if timeframe not in {"1s", "5s", "15s"}:
            raise ValueError(f"Unsupported raw trade timeframe: {timeframe}")

        bucket_seconds = TIMEFRAME_SECONDS[timeframe]
        statement = self._raw_trade_rollup_sql(bucket_seconds)
        params = {
            "exchange": exchange,
            "market_type": market_type,
            "instrument_id": instrument_id,
            "from_ms": from_ms,
            "to_ms": to_ms,
        }
        previous_statement = """
            SELECT price
            FROM raw_trades
            WHERE exchange = :exchange
              AND market_type = :market_type
              AND instrument_id = :instrument_id
              AND exchange_time < to_timestamp(:from_ms / 1000.0)
            ORDER BY exchange_time DESC, sequence DESC NULLS LAST, trade_id DESC
            LIMIT 1
        """

        try:
            async with self.engine.connect() as connection:
                result = await connection.execute(text(statement), params)
                rows = list(result.mappings().all())
                previous_result = await connection.execute(
                    text(previous_statement),
                    params,
                )
                previous_close = previous_result.scalar_one_or_none()
            self.connected = True
            self.last_error = None
        except Exception as error:
            self.connected = False
            self.last_error = str(error)
            raise

        return self._raw_trade_rows_to_history_page(
            rows,
            exchange=exchange,
            market_type=market_type,
            instrument_id=instrument_id,
            timeframe=timeframe,
            from_ms=from_ms,
            to_ms=to_ms,
            limit=limit,
            previous_close=previous_close,
        )

    async def repair_one_second_candles_from_raw_trades(
        self,
        *,
        exchange: str,
        market_type: str,
        instrument_id: str,
        from_ms: int,
        to_ms: int,
    ) -> int:
        if self.engine is None or to_ms <= from_ms:
            return 0

        params = {
            "exchange": exchange,
            "market_type": market_type,
            "instrument_id": instrument_id,
            "from_ms": from_ms,
            "to_ms": to_ms,
        }
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(self._mark_repaired_second_candles_stale_sql()),
                    params,
                )
                result = await connection.execute(
                    text(self._repair_one_second_candles_sql()),
                    params,
                )
                repaired_count = int(result.scalar_one())
            self.connected = True
            self.last_error = None
            self.written_candles += repaired_count
            return repaired_count
        except Exception as error:
            self.connected = False
            self.last_error = str(error)
            raise

    async def _run(self) -> None:
        while True:
            first = await self.queue.get()
            batch = [first]
            while len(batch) < self.batch_size:
                try:
                    batch.append(self.queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            try:
                await self._write_batch(batch)
                self.last_error = None
                self.connected = True
            except Exception as error:
                self.last_error = str(error)
                self.connected = False
                await asyncio.sleep(1)
                for event in batch:
                    await self.queue.put(event)
            finally:
                for _ in batch:
                    self.queue.task_done()

    async def _write_batch(self, batch: List[DatabaseEvent]) -> None:
        if self.engine is None:
            return

        trades = [
            self._trade_params(value)
            for kind, value in batch
            if kind == "trade" and isinstance(value, Trade)
        ]
        candles = [
            value
            for kind, value in batch
            if kind == "candle" and isinstance(value, Candle)
        ]
        metric_snapshots = [
            value
            for kind, value in batch
            if kind == "metrics" and isinstance(value, dict)
        ]

        async with self.engine.begin() as connection:
            if trades:
                await connection.execute(
                    text(
                        """
                        INSERT INTO raw_trades (
                            exchange, market_type, instrument_id, exchange_symbol,
                            trade_id, exchange_time, received_time, price,
                            base_quantity, quote_quantity, side, sequence
                        ) VALUES (
                            :exchange, :market_type, :instrument_id, :exchange_symbol,
                            :trade_id, to_timestamp(:exchange_timestamp_ms / 1000.0),
                            to_timestamp(:received_timestamp_ms / 1000.0), :price,
                            :base_quantity, :quote_quantity, :side, :sequence
                        )
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    trades,
                )
                self.written_trades += len(trades)

            for candle in candles:
                params = self._candle_params(candle)
                await connection.execute(
                    text(
                        """
                        UPDATE candles
                        SET current = FALSE
                        WHERE exchange = :exchange
                          AND market_type = :market_type
                          AND instrument_id = :instrument_id
                          AND timeframe = :timeframe
                          AND open_time = to_timestamp(:open_time_ms / 1000.0)
                          AND current = TRUE
                        """
                    ),
                    params,
                )
                await connection.execute(
                    text(
                        """
                        INSERT INTO candles (
                            exchange, market_type, instrument_id, timeframe,
                            open_time, close_time, open, high, low, close,
                            base_volume, quote_volume, trade_count, status,
                            revision, first_trade_id, last_trade_id,
                            finalized_at, current
                        ) VALUES (
                            :exchange, :market_type, :instrument_id, :timeframe,
                            to_timestamp(:open_time_ms / 1000.0),
                            to_timestamp(:close_time_ms / 1000.0),
                            :open, :high, :low, :close, :base_volume,
                            :quote_volume, :trade_count, :status, :revision,
                            :first_trade_id, :last_trade_id,
                            to_timestamp(:finalized_at_ms / 1000.0), TRUE
                        )
                        ON CONFLICT (
                            exchange, market_type, instrument_id, timeframe,
                            open_time, revision
                        ) DO UPDATE SET
                            close_time = EXCLUDED.close_time,
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            base_volume = EXCLUDED.base_volume,
                            quote_volume = EXCLUDED.quote_volume,
                            trade_count = EXCLUDED.trade_count,
                            status = EXCLUDED.status,
                            first_trade_id = EXCLUDED.first_trade_id,
                            last_trade_id = EXCLUDED.last_trade_id,
                            finalized_at = EXCLUDED.finalized_at,
                            current = TRUE
                        """
                    ),
                    params,
                )
                self.written_candles += 1

            for snapshot in metric_snapshots:
                await self._write_metric_snapshot(connection, snapshot)

    @staticmethod
    def _trade_params(trade: Trade) -> Dict[str, Any]:
        return {
            "exchange": trade.exchange,
            "market_type": trade.market_type,
            "instrument_id": trade.instrument_id,
            "exchange_symbol": trade.exchange_symbol,
            "trade_id": trade.trade_id,
            "exchange_timestamp_ms": trade.exchange_timestamp_ms,
            "received_timestamp_ms": trade.received_timestamp_ms,
            "price": str(trade.price),
            "base_quantity": str(trade.base_quantity),
            "quote_quantity": str(trade.quote_quantity),
            "side": trade.side,
            "sequence": trade.sequence,
        }

    @staticmethod
    def _candle_params(candle: Candle) -> Dict[str, Any]:
        def decimal_value(value: object) -> Optional[str]:
            return None if value is None else str(value)

        return {
            "exchange": candle.exchange,
            "market_type": candle.market_type,
            "instrument_id": candle.instrument_id,
            "timeframe": candle.timeframe,
            "open_time_ms": candle.open_time_ms,
            "close_time_ms": candle.close_time_ms,
            "open": decimal_value(candle.open),
            "high": decimal_value(candle.high),
            "low": decimal_value(candle.low),
            "close": decimal_value(candle.close),
            "base_volume": str(candle.base_volume),
            "quote_volume": str(candle.quote_volume),
            "trade_count": candle.trade_count,
            "status": candle.status,
            "revision": candle.revision,
            "first_trade_id": candle.first_trade_id,
            "last_trade_id": candle.last_trade_id,
            "finalized_at_ms": candle.finalized_at_ms,
        }

    def health(self) -> Dict[str, object]:
        if not self.database_url:
            status = "disabled"
        elif self.connected:
            status = "ok"
        else:
            status = "degraded"
        return {
            "status": status,
            "queueSize": self.queue.qsize(),
            "queueCapacity": self.queue.maxsize,
            "writtenTrades": self.written_trades,
            "writtenCandles": self.written_candles,
            "writtenMetricPoints": self.written_metric_points,
            "writtenMetricEvents": self.written_metric_events,
            "writtenMetricSummaries": self.written_metric_summaries,
            "lastError": self.last_error,
        }

    async def _write_metric_snapshot(
        self,
        connection: Any,
        snapshot: Dict[str, Any],
    ) -> None:
        response = snapshot["response"]
        source_candles = {
            int(candle["openTime"]): candle
            for candle in snapshot.get("sourceCandles", [])
        }
        calculated_at = int(snapshot["calculatedAt"])
        points = [
            self._metric_point_params(
                response,
                point,
                source_candles.get(int(point["openTime"])),
                calculated_at,
            )
            for point in response.get("points", [])
        ]
        if points:
            await connection.execute(
                text(
                    """
                    INSERT INTO metric_points (
                        exchange, market_type, instrument_id, timeframe,
                        metrics_version, open_time, close_time, close, vwap,
                        vwap_deviation_pct, realized_volatility_pct,
                        parkinson_volatility_pct, garman_klass_volatility_pct,
                        rsi, short_momentum_pct, momentum_pct,
                        mean_reversion_z_score, distance_to_mean_pct,
                        price_volume_divergence_pct, volume_spike_ratio,
                        base_volume, trade_count, status, source,
                        source_candle_revision, source_candle_status,
                        source_candle_finalized_at, calculated_at
                    ) VALUES (
                        :exchange, :market_type, :instrument_id, :timeframe,
                        :metrics_version,
                        to_timestamp(:open_time_ms / 1000.0),
                        to_timestamp(:close_time_ms / 1000.0),
                        :close, :vwap, :vwap_deviation_pct,
                        :realized_volatility_pct,
                        :parkinson_volatility_pct,
                        :garman_klass_volatility_pct,
                        :rsi, :short_momentum_pct, :momentum_pct,
                        :mean_reversion_z_score, :distance_to_mean_pct,
                        :price_volume_divergence_pct, :volume_spike_ratio,
                        :base_volume, :trade_count, :status, :source,
                        :source_candle_revision, :source_candle_status,
                        to_timestamp(:source_candle_finalized_at_ms / 1000.0),
                        to_timestamp(:calculated_at_ms / 1000.0)
                    )
                    ON CONFLICT (
                        exchange, market_type, instrument_id, timeframe,
                        metrics_version, open_time
                    ) DO UPDATE SET
                        close_time = EXCLUDED.close_time,
                        close = EXCLUDED.close,
                        vwap = EXCLUDED.vwap,
                        vwap_deviation_pct = EXCLUDED.vwap_deviation_pct,
                        realized_volatility_pct =
                            EXCLUDED.realized_volatility_pct,
                        parkinson_volatility_pct =
                            EXCLUDED.parkinson_volatility_pct,
                        garman_klass_volatility_pct =
                            EXCLUDED.garman_klass_volatility_pct,
                        rsi = EXCLUDED.rsi,
                        short_momentum_pct = EXCLUDED.short_momentum_pct,
                        momentum_pct = EXCLUDED.momentum_pct,
                        mean_reversion_z_score =
                            EXCLUDED.mean_reversion_z_score,
                        distance_to_mean_pct = EXCLUDED.distance_to_mean_pct,
                        price_volume_divergence_pct =
                            EXCLUDED.price_volume_divergence_pct,
                        volume_spike_ratio = EXCLUDED.volume_spike_ratio,
                        base_volume = EXCLUDED.base_volume,
                        trade_count = EXCLUDED.trade_count,
                        status = EXCLUDED.status,
                        source = EXCLUDED.source,
                        source_candle_revision =
                            EXCLUDED.source_candle_revision,
                        source_candle_status = EXCLUDED.source_candle_status,
                        source_candle_finalized_at =
                            EXCLUDED.source_candle_finalized_at,
                        calculated_at = EXCLUDED.calculated_at
                    """
                ),
                points,
            )
            self.written_metric_points += len(points)

        events = snapshot.get("allEvents", response.get("events", []))
        event_params = [
            self._metric_event_params(response, event, calculated_at)
            for event in events
        ]
        await connection.execute(
            text(
                """
                DELETE FROM metric_events
                WHERE exchange = :exchange
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = :timeframe
                  AND metrics_version = :metrics_version
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
                """
            ),
            {
                "exchange": response["exchange"],
                "market_type": snapshot["marketType"],
                "instrument_id": response["instrumentId"],
                "timeframe": response["timeframe"],
                "metrics_version": response["version"],
                "from_ms": response["from"],
                "to_ms": response["to"],
            },
        )
        if event_params:
            await connection.execute(
                text(
                    """
                    INSERT INTO metric_events (
                        exchange, market_type, instrument_id, timeframe,
                        metrics_version, open_time, event_key, close_time,
                        type, metric, severity, confidence, value, threshold,
                        description, calculated_at
                    ) VALUES (
                        :exchange, :market_type, :instrument_id, :timeframe,
                        :metrics_version,
                        to_timestamp(:open_time_ms / 1000.0),
                        :event_key,
                        to_timestamp(:close_time_ms / 1000.0),
                        :type, :metric, :severity, :confidence, :value,
                        :threshold, :description,
                        to_timestamp(:calculated_at_ms / 1000.0)
                    )
                    ON CONFLICT (
                        exchange, market_type, instrument_id, timeframe,
                        metrics_version, open_time, event_key
                    ) DO UPDATE SET
                        close_time = EXCLUDED.close_time,
                        type = EXCLUDED.type,
                        metric = EXCLUDED.metric,
                        severity = EXCLUDED.severity,
                        confidence = EXCLUDED.confidence,
                        value = EXCLUDED.value,
                        threshold = EXCLUDED.threshold,
                        description = EXCLUDED.description,
                        calculated_at = EXCLUDED.calculated_at
                    """
                ),
                event_params,
            )
            self.written_metric_events += len(event_params)

        summary = self._metric_summary_params(snapshot)
        await connection.execute(
            text(
                """
                INSERT INTO metric_summaries (
                    exchange, market_type, instrument_id, timeframe,
                    metrics_version, window_name, window_start, window_end,
                    point_count, source, summary, latest, windows, events,
                    cross_pair_correlations, calculated_at, compute_duration_ms,
                    updated_at
                ) VALUES (
                    :exchange, :market_type, :instrument_id, :timeframe,
                    :metrics_version, :window_name,
                    to_timestamp(:window_start_ms / 1000.0),
                    to_timestamp(:window_end_ms / 1000.0),
                    :point_count, :source, CAST(:summary AS jsonb),
                    CAST(:latest AS jsonb), CAST(:windows AS jsonb),
                    CAST(:events AS jsonb),
                    CAST(:cross_pair_correlations AS jsonb),
                    to_timestamp(:calculated_at_ms / 1000.0),
                    :compute_duration_ms,
                    NOW()
                )
                ON CONFLICT (
                    exchange, market_type, instrument_id, timeframe,
                    metrics_version, window_name
                ) DO UPDATE SET
                    window_start = EXCLUDED.window_start,
                    window_end = EXCLUDED.window_end,
                    point_count = EXCLUDED.point_count,
                    source = EXCLUDED.source,
                    summary = EXCLUDED.summary,
                    latest = EXCLUDED.latest,
                    windows = EXCLUDED.windows,
                    events = EXCLUDED.events,
                    cross_pair_correlations =
                        EXCLUDED.cross_pair_correlations,
                    calculated_at = EXCLUDED.calculated_at,
                    compute_duration_ms = EXCLUDED.compute_duration_ms,
                    updated_at = NOW()
                """
            ),
            summary,
        )
        self.written_metric_summaries += 1

    @staticmethod
    def _metric_point_params(
        response: Dict[str, Any],
        point: Dict[str, Any],
        candle: Optional[Dict[str, Any]],
        calculated_at_ms: int,
    ) -> Dict[str, Any]:
        return {
            "exchange": response["exchange"],
            "market_type": response["marketType"],
            "instrument_id": response["instrumentId"],
            "timeframe": response["timeframe"],
            "metrics_version": response["version"],
            "open_time_ms": int(point["openTime"]),
            "close_time_ms": int(point["closeTime"]),
            "close": point.get("close"),
            "vwap": point.get("vwap"),
            "vwap_deviation_pct": point.get("vwapDeviationPct"),
            "realized_volatility_pct": point.get("realizedVolatilityPct"),
            "parkinson_volatility_pct": point.get("parkinsonVolatilityPct"),
            "garman_klass_volatility_pct": point.get("garmanKlassVolatilityPct"),
            "rsi": point.get("rsi"),
            "short_momentum_pct": point.get("shortMomentumPct"),
            "momentum_pct": point.get("momentumPct"),
            "mean_reversion_z_score": point.get("meanReversionZScore"),
            "distance_to_mean_pct": point.get("distanceToMeanPct"),
            "price_volume_divergence_pct": point.get("priceVolumeDivergencePct"),
            "volume_spike_ratio": point.get("volumeSpikeRatio"),
            "base_volume": point.get("baseVolume"),
            "trade_count": int(point.get("tradeCount", 0)),
            "status": point.get("status"),
            "source": candle.get("source") if candle else response.get("source"),
            "source_candle_revision": (
                int(candle["revision"]) if candle and candle.get("revision") else None
            ),
            "source_candle_status": candle.get("status") if candle else None,
            "source_candle_finalized_at_ms": (
                int(candle["finalizedAt"])
                if candle and candle.get("finalizedAt")
                else int(point["closeTime"])
            ),
            "calculated_at_ms": calculated_at_ms,
        }

    @staticmethod
    def _metric_event_params(
        response: Dict[str, Any],
        event: Dict[str, Any],
        calculated_at_ms: int,
    ) -> Dict[str, Any]:
        event_key = f"{event['type']}:{event['metric']}"
        return {
            "exchange": response["exchange"],
            "market_type": response["marketType"],
            "instrument_id": response["instrumentId"],
            "timeframe": response["timeframe"],
            "metrics_version": response["version"],
            "open_time_ms": int(event["openTime"]),
            "close_time_ms": int(event["closeTime"]),
            "event_key": event_key,
            "type": event["type"],
            "metric": event["metric"],
            "severity": event["severity"],
            "confidence": event.get("confidence"),
            "value": event.get("value"),
            "threshold": event.get("threshold"),
            "description": event["description"],
            "calculated_at_ms": calculated_at_ms,
        }

    @staticmethod
    def _metric_summary_params(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        response = snapshot["response"]
        return {
            "exchange": response["exchange"],
            "market_type": response["marketType"],
            "instrument_id": response["instrumentId"],
            "timeframe": response["timeframe"],
            "metrics_version": response["version"],
            "window_name": snapshot["windowName"],
            "window_start_ms": response["from"],
            "window_end_ms": response["to"],
            "point_count": int(response["count"]),
            "source": response["source"],
            "summary": json.dumps(response["summary"]),
            "latest": json.dumps(response["latest"]),
            "windows": json.dumps(response["windows"]),
            "events": json.dumps(response["events"]),
            "cross_pair_correlations": json.dumps(response["crossPairCorrelations"]),
            "calculated_at_ms": int(snapshot["calculatedAt"]),
            "compute_duration_ms": int(snapshot["computeDurationMs"]),
        }

    @staticmethod
    def _history_page_source(rows: List[Mapping[str, Any]]) -> str:
        sources = {
            str(row.get("history_source"))
            for row in rows
            if row.get("history_source") is not None
        }
        if "binance_proxy_1s" in sources:
            return "binance_proxy_1s"
        if "historical_candles" in sources:
            return "historical_candles"
        return "timescaledb"

    @staticmethod
    def _one_second_history_sql() -> str:
        return """
            WITH live AS (
                SELECT
                    exchange,
                    market_type,
                    instrument_id,
                    open_time,
                    close_time,
                    open,
                    high,
                    low,
                    close,
                    base_volume,
                    quote_volume,
                    trade_count,
                    status,
                    revision,
                    first_trade_id,
                    last_trade_id,
                    finalized_at,
                    1::BIGINT AS source_candle_count,
                    CASE WHEN status = 'incomplete' THEN 1 ELSE 0 END::BIGINT
                        AS incomplete_count,
                    CASE WHEN status = 'recovered' THEN 1 ELSE 0 END::BIGINT
                        AS recovered_count,
                    2 AS priority,
                    'timescaledb'::TEXT AS history_source
                FROM candles
                WHERE exchange = :exchange
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = '1s'
                  AND current = TRUE
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
            ),
            historical AS (
                SELECT
                    :exchange AS exchange,
                    market_type,
                    instrument_id,
                    open_time,
                    close_time,
                    open,
                    high,
                    low,
                    close,
                    base_volume,
                    quote_volume,
                    trade_count,
                    status,
                    revision,
                    NULL::TEXT AS first_trade_id,
                    NULL::TEXT AS last_trade_id,
                    finalized_at,
                    1::BIGINT AS source_candle_count,
                    CASE WHEN status = 'incomplete' THEN 1 ELSE 0 END::BIGINT
                        AS incomplete_count,
                    CASE WHEN status = 'recovered' THEN 1 ELSE 0 END::BIGINT
                        AS recovered_count,
                    3 AS priority,
                    'historical_candles'::TEXT AS history_source
                FROM historical_candles
                WHERE exchange = :exchange
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = '1s'
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
            ),
            binance_proxy AS (
                SELECT
                    :exchange AS exchange,
                    market_type,
                    instrument_id,
                    open_time,
                    close_time,
                    open,
                    high,
                    low,
                    close,
                    base_volume,
                    quote_volume,
                    trade_count,
                    status,
                    revision,
                    NULL::TEXT AS first_trade_id,
                    NULL::TEXT AS last_trade_id,
                    finalized_at,
                    1::BIGINT AS source_candle_count,
                    CASE WHEN status = 'incomplete' THEN 1 ELSE 0 END::BIGINT
                        AS incomplete_count,
                    CASE WHEN status = 'recovered' THEN 1 ELSE 0 END::BIGINT
                        AS recovered_count,
                    1 AS priority,
                    'binance_proxy_1s'::TEXT AS history_source
                FROM historical_candles
                WHERE :exchange = 'bybit'
                  AND exchange = 'binance'
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = '1s'
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
            ),
            combined AS (
                SELECT * FROM live
                UNION ALL
                SELECT * FROM historical
                UNION ALL
                SELECT * FROM binance_proxy
            ),
            ranked AS (
                SELECT
                    *,
                    row_number() OVER (
                        PARTITION BY open_time
                        ORDER BY priority DESC, finalized_at DESC
                    ) AS row_rank
                FROM combined
            )
            SELECT
                exchange,
                market_type,
                instrument_id,
                open_time,
                close_time,
                open,
                high,
                low,
                close,
                base_volume,
                quote_volume,
                trade_count,
                status,
                revision,
                first_trade_id,
                last_trade_id,
                finalized_at,
                source_candle_count,
                incomplete_count,
                recovered_count,
                history_source
            FROM ranked
            WHERE row_rank = 1
            ORDER BY open_time DESC
            LIMIT :fetch_limit
        """

    @staticmethod
    def _raw_trade_rollup_sql(bucket_seconds: int) -> str:
        return f"""
            SELECT
                time_bucket(
                    INTERVAL '{bucket_seconds} seconds',
                    exchange_time
                ) AS open_time,
                (array_agg(
                    price
                    ORDER BY exchange_time ASC, sequence ASC NULLS LAST,
                        trade_id ASC
                ))[1] AS open,
                max(price) AS high,
                min(price) AS low,
                (array_agg(
                    price
                    ORDER BY exchange_time DESC, sequence DESC NULLS LAST,
                        trade_id DESC
                ))[1] AS close,
                sum(base_quantity) AS base_volume,
                sum(quote_quantity) AS quote_volume,
                count(*)::BIGINT AS trade_count,
                (array_agg(
                    trade_id
                    ORDER BY exchange_time ASC, sequence ASC NULLS LAST,
                        trade_id ASC
                ))[1] AS first_trade_id,
                (array_agg(
                    trade_id
                    ORDER BY exchange_time DESC, sequence DESC NULLS LAST,
                        trade_id DESC
                ))[1] AS last_trade_id,
                max(received_time) AS finalized_at
            FROM raw_trades
            WHERE exchange = :exchange
              AND market_type = :market_type
              AND instrument_id = :instrument_id
              AND exchange_time >= to_timestamp(:from_ms / 1000.0)
              AND exchange_time < to_timestamp(:to_ms / 1000.0)
            GROUP BY time_bucket(
                INTERVAL '{bucket_seconds} seconds',
                exchange_time
            )
            ORDER BY open_time ASC
        """

    @staticmethod
    def _raw_one_second_repair_rollup_sql() -> str:
        return """
            SELECT
                time_bucket(INTERVAL '1 second', exchange_time) AS open_time,
                (array_agg(
                    price
                    ORDER BY exchange_time ASC, sequence ASC NULLS LAST,
                        trade_id ASC
                ))[1] AS open,
                max(price) AS high,
                min(price) AS low,
                (array_agg(
                    price
                    ORDER BY exchange_time DESC, sequence DESC NULLS LAST,
                        trade_id DESC
                ))[1] AS close,
                sum(base_quantity) AS base_volume,
                sum(quote_quantity) AS quote_volume,
                count(*)::BIGINT AS trade_count,
                (array_agg(
                    trade_id
                    ORDER BY exchange_time ASC, sequence ASC NULLS LAST,
                        trade_id ASC
                ))[1] AS first_trade_id,
                (array_agg(
                    trade_id
                    ORDER BY exchange_time DESC, sequence DESC NULLS LAST,
                        trade_id DESC
                ))[1] AS last_trade_id,
                max(received_time) AS finalized_at
            FROM raw_trades
            WHERE exchange = :exchange
              AND market_type = :market_type
              AND instrument_id = :instrument_id
              AND exchange_time >= to_timestamp(:from_ms / 1000.0)
              AND exchange_time < to_timestamp(:to_ms / 1000.0)
            GROUP BY time_bucket(INTERVAL '1 second', exchange_time)
        """

    @staticmethod
    def _mark_repaired_second_candles_stale_sql() -> str:
        return f"""
            WITH rolled AS (
                {DatabaseWriter._raw_one_second_repair_rollup_sql()}
            )
            UPDATE candles
            SET current = FALSE
            FROM rolled
            WHERE candles.exchange = :exchange
              AND candles.market_type = :market_type
              AND candles.instrument_id = :instrument_id
              AND candles.timeframe = '1s'
              AND candles.open_time = rolled.open_time
              AND candles.current = TRUE
        """

    @staticmethod
    def _repair_one_second_candles_sql() -> str:
        return f"""
            WITH rolled AS (
                {DatabaseWriter._raw_one_second_repair_rollup_sql()}
            ),
            existing AS (
                SELECT
                    open_time,
                    max(revision) AS revision
                FROM candles
                WHERE exchange = :exchange
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = '1s'
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
                GROUP BY open_time
            ),
            repaired AS (
                SELECT
                    :exchange AS exchange,
                    :market_type AS market_type,
                    :instrument_id AS instrument_id,
                    '1s' AS timeframe,
                    rolled.open_time AS open_time,
                    rolled.open_time + INTERVAL '1 second' AS close_time,
                    rolled.open,
                    rolled.high,
                    rolled.low,
                    rolled.close,
                    rolled.base_volume,
                    rolled.quote_volume,
                    rolled.trade_count,
                    'complete' AS status,
                    COALESCE(existing.revision, 1) AS revision,
                    rolled.first_trade_id,
                    rolled.last_trade_id,
                    rolled.finalized_at
                FROM rolled
                LEFT JOIN existing ON existing.open_time = rolled.open_time
            ),
            upserted AS (
                INSERT INTO candles (
                    exchange, market_type, instrument_id, timeframe,
                    open_time, close_time, open, high, low, close,
                    base_volume, quote_volume, trade_count, status,
                    revision, first_trade_id, last_trade_id,
                    finalized_at, current
                )
                SELECT
                    exchange, market_type, instrument_id, timeframe,
                    open_time, close_time, open, high, low, close,
                    base_volume, quote_volume, trade_count, status,
                    revision, first_trade_id, last_trade_id,
                    finalized_at, TRUE
                FROM repaired
                ON CONFLICT (
                    exchange, market_type, instrument_id, timeframe,
                    open_time, revision
                ) DO UPDATE SET
                    close_time = EXCLUDED.close_time,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    base_volume = EXCLUDED.base_volume,
                    quote_volume = EXCLUDED.quote_volume,
                    trade_count = EXCLUDED.trade_count,
                    status = EXCLUDED.status,
                    first_trade_id = EXCLUDED.first_trade_id,
                    last_trade_id = EXCLUDED.last_trade_id,
                    finalized_at = EXCLUDED.finalized_at,
                    current = TRUE
                RETURNING 1
            )
            SELECT count(*)::BIGINT FROM upserted
        """

    @staticmethod
    def _raw_trade_rows_to_history_page(
        rows: List[Mapping[str, Any]],
        *,
        exchange: str,
        market_type: str,
        instrument_id: str,
        timeframe: str,
        from_ms: int,
        to_ms: int,
        limit: int,
        previous_close: Optional[Decimal],
    ) -> HistoryPage:
        bucket_ms = timeframe_ms(timeframe)
        rows_by_open = {_datetime_ms(row["open_time"]): row for row in rows}
        candles: List[Dict[str, Any]] = []
        carry_close = previous_close

        start_ms = (from_ms // bucket_ms) * bucket_ms
        end_ms = (to_ms // bucket_ms) * bucket_ms
        for open_time_ms in range(start_ms, end_ms, bucket_ms):
            row = rows_by_open.get(open_time_ms)
            close_time_ms = open_time_ms + bucket_ms
            if row is None:
                if carry_close is None:
                    continue
                candles.append(
                    {
                        "exchange": exchange,
                        "marketType": market_type,
                        "instrumentId": instrument_id,
                        "timeframe": timeframe,
                        "openTime": open_time_ms,
                        "closeTime": close_time_ms,
                        "open": str(carry_close),
                        "high": str(carry_close),
                        "low": str(carry_close),
                        "close": str(carry_close),
                        "baseVolume": "0",
                        "quoteVolume": "0",
                        "tradeCount": 0,
                        "status": "complete_empty",
                        "revision": 1,
                        "firstTradeId": None,
                        "lastTradeId": None,
                        "finalizedAt": close_time_ms,
                    }
                )
                continue

            carry_close = row["close"]
            candles.append(
                {
                    "exchange": exchange,
                    "marketType": market_type,
                    "instrumentId": instrument_id,
                    "timeframe": timeframe,
                    "openTime": open_time_ms,
                    "closeTime": close_time_ms,
                    "open": _decimal_string(row["open"]),
                    "high": _decimal_string(row["high"]),
                    "low": _decimal_string(row["low"]),
                    "close": _decimal_string(row["close"]),
                    "baseVolume": _decimal_string(row["base_volume"]) or "0",
                    "quoteVolume": _decimal_string(row["quote_volume"]) or "0",
                    "tradeCount": int(row["trade_count"]),
                    "status": "complete",
                    "revision": 1,
                    "firstTradeId": row.get("first_trade_id"),
                    "lastTradeId": row.get("last_trade_id"),
                    "finalizedAt": _datetime_ms(row["finalized_at"]),
                }
            )

        has_more = len(candles) > limit or previous_close is not None
        if len(candles) > limit:
            candles = candles[-limit:]
        return HistoryPage(
            candles=candles,
            has_more=has_more,
            source="raw_trades",
        )

    @staticmethod
    def _runtime_rollup_sql(timeframe: str) -> str:
        interval = SQL_INTERVALS[timeframe]
        return f"""
            WITH live AS (
                SELECT
                    exchange,
                    market_type,
                    instrument_id,
                    open_time,
                    open,
                    high,
                    low,
                    close,
                    base_volume,
                    quote_volume,
                    trade_count,
                    status,
                    revision,
                    finalized_at,
                    2 AS priority,
                    'timescaledb'::TEXT AS history_source
                FROM candles
                WHERE exchange = :exchange
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = '1s'
                  AND current = TRUE
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
            ),
            historical AS (
                SELECT
                    :exchange AS exchange,
                    market_type,
                    instrument_id,
                    open_time,
                    open,
                    high,
                    low,
                    close,
                    base_volume,
                    quote_volume,
                    trade_count,
                    status,
                    revision,
                    finalized_at,
                    3 AS priority,
                    'historical_candles'::TEXT AS history_source
                FROM historical_candles
                WHERE exchange = :exchange
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = '1s'
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
            ),
            binance_proxy AS (
                SELECT
                    :exchange AS exchange,
                    market_type,
                    instrument_id,
                    open_time,
                    open,
                    high,
                    low,
                    close,
                    base_volume,
                    quote_volume,
                    trade_count,
                    status,
                    revision,
                    finalized_at,
                    1 AS priority,
                    'binance_proxy_1s'::TEXT AS history_source
                FROM historical_candles
                WHERE :exchange = 'bybit'
                  AND exchange = 'binance'
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND timeframe = '1s'
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
            ),
            combined AS (
                SELECT * FROM live
                UNION ALL
                SELECT * FROM historical
                UNION ALL
                SELECT * FROM binance_proxy
            ),
            ranked AS (
                SELECT
                    *,
                    row_number() OVER (
                        PARTITION BY open_time
                        ORDER BY priority DESC, finalized_at DESC
                    ) AS row_rank
                FROM combined
            ),
            source AS (
                SELECT *
                FROM ranked
                WHERE row_rank = 1
                ORDER BY open_time DESC
                LIMIT :source_fetch_limit
            )
            SELECT
                exchange,
                market_type,
                instrument_id,
                time_bucket(INTERVAL '{interval}', open_time) AS open_time,
                time_bucket(INTERVAL '{interval}', open_time)
                    + INTERVAL '{interval}' AS close_time,
                first(open, open_time) FILTER (WHERE open IS NOT NULL) AS open,
                max(high) AS high,
                min(low) AS low,
                last(close, open_time) FILTER (WHERE close IS NOT NULL) AS close,
                sum(base_volume) AS base_volume,
                sum(quote_volume) AS quote_volume,
                sum(trade_count)::BIGINT AS trade_count,
                max(revision) AS revision,
                max(finalized_at) AS finalized_at,
                count(*)::BIGINT AS source_candle_count,
                count(*) FILTER (
                    WHERE status = 'incomplete'
                )::BIGINT AS incomplete_count,
                count(*) FILTER (
                    WHERE status = 'recovered'
                )::BIGINT AS recovered_count,
                NULL::TEXT AS first_trade_id,
                NULL::TEXT AS last_trade_id,
                NULL::TEXT AS status,
                CASE
                    WHEN count(*) FILTER (
                        WHERE history_source = 'binance_proxy_1s'
                    ) > 0 THEN 'binance_proxy_1s'
                    WHEN count(*) FILTER (
                        WHERE history_source = 'historical_candles'
                    ) > 0 THEN 'historical_candles'
                    ELSE 'timescaledb'
                END::TEXT AS history_source
            FROM source
            GROUP BY
                exchange,
                market_type,
                instrument_id,
                time_bucket(INTERVAL '{interval}', open_time)
            ORDER BY open_time DESC
            LIMIT :fetch_limit
        """

    @staticmethod
    def _persisted_rollup_sql(timeframe: str) -> str:
        view_name = ROLLUP_VIEWS[timeframe]
        interval_seconds = TIMEFRAME_SECONDS[timeframe]
        interval_minutes = interval_seconds // 60
        historical_sql = (
            DatabaseWriter._historical_one_minute_sql(interval_seconds)
            if timeframe == "1m"
            else DatabaseWriter._historical_minute_rollup_sql(
                timeframe,
                interval_seconds,
                interval_minutes,
            )
        )
        return f"""
            WITH persisted AS (
                SELECT
                    exchange,
                    market_type,
                    instrument_id,
                    open_time,
                    open_time + INTERVAL '{interval_seconds} seconds'
                        AS close_time,
                    open,
                    high,
                    low,
                    close,
                    base_volume,
                    quote_volume,
                    trade_count,
                    revision,
                    finalized_at,
                    source_candle_count,
                    incomplete_count,
                    recovered_count,
                    NULL::TEXT AS first_trade_id,
                    NULL::TEXT AS last_trade_id,
                    NULL::TEXT AS status,
                    1 AS priority
                FROM {view_name}
                WHERE exchange = :exchange
                  AND market_type = :market_type
                  AND instrument_id = :instrument_id
                  AND open_time >= to_timestamp(:from_ms / 1000.0)
                  AND open_time < to_timestamp(:to_ms / 1000.0)
            ),
            historical AS (
                {historical_sql}
            ),
            combined AS (
                SELECT * FROM persisted
                UNION ALL
                SELECT * FROM historical
            ),
            ranked AS (
                SELECT
                    *,
                    row_number() OVER (
                        PARTITION BY open_time
                        ORDER BY priority DESC
                    ) AS row_rank
                FROM combined
            )
            SELECT
                exchange,
                market_type,
                instrument_id,
                open_time,
                close_time,
                open,
                high,
                low,
                close,
                base_volume,
                quote_volume,
                trade_count,
                revision,
                finalized_at,
                source_candle_count,
                incomplete_count,
                recovered_count,
                first_trade_id,
                last_trade_id,
                status
            FROM ranked
            WHERE row_rank = 1
            ORDER BY open_time DESC
            LIMIT :fetch_limit
        """

    @staticmethod
    def _historical_one_minute_sql(interval_seconds: int) -> str:
        return f"""
            SELECT
                exchange,
                market_type,
                instrument_id,
                open_time,
                open_time + INTERVAL '{interval_seconds} seconds'
                    AS close_time,
                open,
                high,
                low,
                close,
                base_volume,
                quote_volume,
                trade_count::BIGINT AS trade_count,
                revision,
                finalized_at,
                {interval_seconds}::BIGINT AS source_candle_count,
                CASE WHEN status = 'incomplete' THEN 1 ELSE 0 END::BIGINT
                    AS incomplete_count,
                CASE WHEN status = 'recovered' THEN 1 ELSE 0 END::BIGINT
                    AS recovered_count,
                NULL::TEXT AS first_trade_id,
                NULL::TEXT AS last_trade_id,
                status,
                2 AS priority
            FROM historical_candles
            WHERE exchange = :exchange
              AND market_type = :market_type
              AND instrument_id = :instrument_id
              AND timeframe = '1m'
              AND open_time >= to_timestamp(:from_ms / 1000.0)
              AND open_time < to_timestamp(:to_ms / 1000.0)
        """

    @staticmethod
    def _historical_minute_rollup_sql(
        timeframe: str,
        interval_seconds: int,
        interval_minutes: int,
    ) -> str:
        return f"""
            SELECT
                exchange,
                market_type,
                instrument_id,
                time_bucket(
                    INTERVAL '{interval_seconds} seconds',
                    open_time
                ) AS open_time,
                time_bucket(
                    INTERVAL '{interval_seconds} seconds',
                    open_time
                ) + INTERVAL '{interval_seconds} seconds' AS close_time,
                first(open, open_time) AS open,
                max(high) AS high,
                min(low) AS low,
                last(close, open_time) AS close,
                sum(base_volume) AS base_volume,
                sum(quote_volume) AS quote_volume,
                sum(trade_count)::BIGINT AS trade_count,
                max(revision) AS revision,
                max(finalized_at) AS finalized_at,
                count(*)::BIGINT AS source_candle_count,
                count(*) FILTER (
                    WHERE status = 'incomplete'
                )::BIGINT AS incomplete_count,
                count(*) FILTER (
                    WHERE status = 'recovered'
                )::BIGINT AS recovered_count,
                NULL::TEXT AS first_trade_id,
                NULL::TEXT AS last_trade_id,
                CASE
                    WHEN count(*) < {interval_minutes}
                      OR count(*) FILTER (WHERE status = 'incomplete') > 0
                        THEN 'incomplete'
                    WHEN count(*) FILTER (WHERE status = 'recovered') > 0
                        THEN 'recovered'
                    WHEN sum(trade_count) = 0
                        THEN 'complete_empty'
                    ELSE 'complete'
                END::TEXT AS status,
                2 AS priority
            FROM historical_candles
            WHERE exchange = :exchange
              AND market_type = :market_type
              AND instrument_id = :instrument_id
              AND timeframe = '1m'
              AND open_time >= to_timestamp(:from_ms / 1000.0)
              AND open_time < to_timestamp(:to_ms / 1000.0)
            GROUP BY
                exchange,
                market_type,
                instrument_id,
                time_bucket(
                    INTERVAL '{interval_seconds} seconds',
                    open_time
                )
        """

    @staticmethod
    def _history_row_to_api(
        row: Mapping[str, Any],
        timeframe: str,
    ) -> Dict[str, Any]:
        expected_count = TIMEFRAME_SECONDS[timeframe]
        source_count = int(row["source_candle_count"])
        trade_count = int(row["trade_count"])
        explicit_status = row.get("status")
        if explicit_status:
            status = str(explicit_status)
        elif source_count < expected_count or int(row["incomplete_count"]) > 0:
            status = "incomplete"
        elif int(row["recovered_count"]) > 0:
            status = "recovered"
        elif trade_count == 0:
            status = "complete_empty"
        else:
            status = "complete"

        return {
            "exchange": row["exchange"],
            "marketType": row["market_type"],
            "instrumentId": row["instrument_id"],
            "timeframe": timeframe,
            "openTime": _datetime_ms(row["open_time"]),
            "closeTime": _datetime_ms(row["close_time"]),
            "open": _decimal_string(row["open"]),
            "high": _decimal_string(row["high"]),
            "low": _decimal_string(row["low"]),
            "close": _decimal_string(row["close"]),
            "baseVolume": _decimal_string(row["base_volume"]) or "0",
            "quoteVolume": _decimal_string(row["quote_volume"]) or "0",
            "tradeCount": trade_count,
            "status": status,
            "revision": int(row["revision"]),
            "firstTradeId": row.get("first_trade_id"),
            "lastTradeId": row.get("last_trade_id"),
            "finalizedAt": _datetime_ms(row["finalized_at"]),
            "source": row.get("history_source"),
        }


def _datetime_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _decimal_string(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else str(value)
