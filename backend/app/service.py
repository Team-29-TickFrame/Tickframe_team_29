import asyncio
import os
import time
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import asyncpg

from backend.scripts.backfill_candles import (
    DEFAULT_LIMIT as RECOVERY_REQUEST_LIMIT,
    INTERVAL_MS as RECOVERY_INTERVAL_MS,
    align_closed_end_ms,
    backfill_market,
    normalize_database_url,
)
from .aggregation import CandleAggregator, StreamKey
from .config import AppConfig
from .database import DatabaseWriter
from .exchanges.base import ExchangeCollector
from .exchanges.binance import BinanceCollector
from .exchanges.bybit import BybitCollector
from .history import (
    TIMEFRAME_SECONDS,
    aggregate_memory_candles,
    resolve_time_range,
    timeframe_ms,
)
from .metrics import compute_metrics, compute_return_correlation
from .models import Trade
from .observability import LatencyObservability, service_prometheus_text
from .store import LiveStore


def unix_ms() -> int:
    return int(time.time() * 1000)


RAW_TRADE_CHART_TIMEFRAMES = {"1s", "5s", "15s"}
DEFAULT_STABLE_CHART_DELAY_MS = 2_000
DEFAULT_SECOND_REPAIR_HOURS = 72.0
DEFAULT_BINANCE_SECOND_BACKFILL_HOURS = 24.0
METRICS_DEFAULT_LIMIT = 300
METRICS_24H_TIMEFRAME = "1m"
METRICS_24H_LIMIT = 24 * 60
METRICS_24H_WINDOW_MS = 24 * 60 * 60 * 1000
CORRELATION_REFRESH_MS = 60_000
MetricScope = Tuple[str, str, str, str]


class MarketDataService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = LiveStore(config)
        self.database = DatabaseWriter()
        self.observability = LatencyObservability()
        self.aggregator = CandleAggregator(
            allowed_lateness_ms=config.allowed_lateness_ms
        )
        self.trade_queue: "asyncio.Queue[Trade]" = asyncio.Queue(maxsize=200_000)
        self.metric_queue: "asyncio.Queue[MetricScope]" = asyncio.Queue(
            maxsize=10_000
        )
        self.collectors: Dict[str, ExchangeCollector] = {
            "binance": BinanceCollector(
                config,
                config.subscriptions_for("binance"),
                self.enqueue_trade,
                self.handle_connection_state,
            ),
            "bybit": BybitCollector(
                config,
                config.subscriptions_for("bybit"),
                self.enqueue_trade,
                self.handle_connection_state,
            ),
        }
        self._disconnected_since: Dict[str, int] = {}
        self._tasks: List[asyncio.Task] = []
        self._pending_metric_scopes: Set[MetricScope] = set()
        self.metric_cache: Dict[MetricScope, Dict[str, object]] = {}
        self.metric_scope_revisions: Dict[MetricScope, int] = {}
        self.correlation_cache: Dict[MetricScope, Dict[str, object]] = {}
        self.metric_revision = 0
        self.market_stream_revision = 0
        self.provisional_candle_revision = 0
        self.stable_candle_revision = 0
        self._stream_condition = asyncio.Condition()
        self._recovery_task: Optional[asyncio.Task] = None
        self._recovery_lock = asyncio.Lock()
        self.recovery_enabled = os.getenv("TICKFRAME_DISABLE_RECOVERY_BACKFILL") != "1"
        self.recovery_lookback_hours = parse_recovery_lookback_hours(
            os.getenv("TICKFRAME_RECOVERY_BACKFILL_HOURS", "72")
        )
        self.stable_chart_delay_ms = parse_duration_ms(
            os.getenv("TICKFRAME_STABLE_CHART_DELAY_MS"),
            DEFAULT_STABLE_CHART_DELAY_MS,
        )
        self.second_repair_hours = min(
            parse_recovery_lookback_hours(
                os.getenv(
                    "TICKFRAME_SECOND_REPAIR_HOURS",
                    os.getenv(
                        "TICKFRAME_RECOVERY_BACKFILL_HOURS",
                        str(DEFAULT_SECOND_REPAIR_HOURS),
                    ),
                )
            ),
            float(config.raw_trade_retention_hours),
        )
        self.binance_second_backfill_hours = parse_recovery_lookback_hours(
            os.getenv(
                "TICKFRAME_BINANCE_1S_BACKFILL_HOURS",
                str(DEFAULT_BINANCE_SECOND_BACKFILL_HOURS),
            )
        )
        self.recovery_status: Dict[str, object] = {
            "enabled": self.recovery_enabled,
            "running": False,
            "lookbackHours": self.recovery_lookback_hours,
            "secondRepairHours": self.second_repair_hours,
            "binanceSecondBackfillHours": self.binance_second_backfill_hours,
            "lastReason": None,
            "lastStartedAt": None,
            "lastFinishedAt": None,
            "insertedCandles": 0,
            "insertedHistoricalSecondCandles": 0,
            "repairedSecondCandles": 0,
            "failedMarkets": {},
            "lastError": None,
        }
        self.processed_trades = 0
        self.revised_candles = 0
        self.computed_metric_snapshots = 0
        self.last_metric_error: Optional[str] = None

    async def start(self) -> None:
        await self.database.start()
        self._tasks = [
            asyncio.create_task(self._consume_trades(), name="trade-consumer"),
            asyncio.create_task(self._finalize_candles(), name="candle-finalizer"),
            asyncio.create_task(self._process_metric_updates(), name="metrics-worker"),
        ]
        for collector in self.collectors.values():
            collector.start()
        self._schedule_recovery("startup", list(self.config.exchanges))

    async def stop(self) -> None:
        for collector in self.collectors.values():
            await collector.stop()
        if self._recovery_task is not None:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
        await self.trade_queue.join()
        await self.metric_queue.join()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self.database.stop()

    async def enqueue_trade(self, trade: Trade) -> None:
        await self.trade_queue.put(trade)

    async def wait_for_market_update(
        self,
        last_revision: int,
        timeout: float = 30.0,
    ) -> int:
        return await self._wait_for_stream_revision(
            "market_stream_revision",
            last_revision,
            timeout,
        )

    async def wait_for_provisional_candle_update(
        self,
        last_revision: int,
        timeout: float = 30.0,
    ) -> int:
        return await self._wait_for_stream_revision(
            "provisional_candle_revision",
            last_revision,
            timeout,
        )

    async def wait_for_stable_candle_update(
        self,
        last_revision: int,
        timeout: float = 30.0,
    ) -> int:
        return await self._wait_for_stream_revision(
            "stable_candle_revision",
            last_revision,
            timeout,
        )

    async def wait_for_metric_update(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        window_name: str,
        last_revision: int,
        timeout: float = 30.0,
    ) -> int:
        scope = (exchange, instrument_id, timeframe, window_name)
        async with self._stream_condition:
            if self.metric_scope_revisions.get(scope, -1) == last_revision:
                try:
                    await asyncio.wait_for(
                        self._stream_condition.wait_for(
                            lambda: self.metric_scope_revisions.get(scope, -1)
                            != last_revision
                        ),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    pass
            return self.metric_scope_revisions.get(scope, -1)

    async def candle_history(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        limit: int,
        from_ms: Optional[int],
        to_ms: Optional[int],
    ) -> Dict[str, object]:
        now_ms = unix_ms()
        resolved_from, resolved_to = resolve_time_range(
            timeframe=timeframe,
            limit=limit,
            now_ms=now_ms,
            from_ms=from_ms,
            to_ms=to_ms,
        )

        page = None
        response_from = resolved_from
        response_to = resolved_to

        try:
            page = await self.database.candle_history(
                exchange=exchange,
                market_type=self.config.market_type,
                instrument_id=instrument_id,
                timeframe=timeframe,
                from_ms=resolved_from,
                to_ms=resolved_to,
                limit=limit,
            )
        except Exception:
            # The live in-memory window keeps the dashboard useful during a
            # database outage, while /health still exposes the degraded DB.
            page = None

        if timeframe in RAW_TRADE_CHART_TIMEFRAMES:
            bucket_ms = timeframe_ms(timeframe)
            stable_to = min(
                resolved_to,
                now_ms - self.stable_chart_delay_ms,
            )
            stable_to = (stable_to // bucket_ms) * bucket_ms
            retention_floor = max(
                0,
                now_ms
                - int(self.config.raw_trade_retention_hours * 60 * 60 * 1000),
            )
            raw_from = max(
                resolved_from,
                retention_floor,
                stable_to - ((limit + 1) * bucket_ms),
            )
            raw_from = (raw_from // bucket_ms) * bucket_ms
            if (
                stable_to > raw_from
                and (
                    page is None
                    or page.source == "timescaledb"
                    or not page.candles
                )
            ):
                try:
                    raw_page = await self.database.raw_trade_candle_history(
                        exchange=exchange,
                        market_type=self.config.market_type,
                        instrument_id=instrument_id,
                        timeframe=timeframe,
                        from_ms=raw_from,
                        to_ms=stable_to,
                        limit=limit,
                    )
                    if raw_page is not None and raw_page.candles:
                        page = raw_page
                        response_from = raw_from
                        response_to = stable_to
                except Exception:
                    pass

        if page is None:
            base_candles = await self.store.candle_snapshot(
                exchange,
                instrument_id,
                self.store.candle_limit,
            )
            page = aggregate_memory_candles(
                base_candles,
                timeframe=timeframe,
                from_ms=resolved_from,
                to_ms=resolved_to,
                limit=limit,
            )

        next_before = (
            page.candles[0]["openTime"]
            if page.candles and page.has_more
            else None
        )
        response = {
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "source": page.source,
            "from": response_from,
            "to": response_to,
            "count": len(page.candles),
            "hasMore": page.has_more,
            "nextBefore": next_before,
            "chartLatency": {
                "generatedAt": now_ms,
                "dataTo": response_to,
                "effectiveLagMs": max(0, now_ms - response_to),
                "stableDelayMs": (
                    self.stable_chart_delay_ms
                    if timeframe in RAW_TRADE_CHART_TIMEFRAMES
                    else 0
                ),
                "allowedLatenessMs": self.config.allowed_lateness_ms,
            },
            "candles": page.candles,
        }
        self.observability.observe_chart_snapshot("candles_rest", response)
        return response

    async def metrics_snapshot(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        limit: int,
        from_ms: Optional[int],
        to_ms: Optional[int],
    ) -> Dict[str, object]:
        window_name = self._metrics_window_name(
            timeframe=timeframe,
            limit=limit,
            from_ms=from_ms,
            to_ms=to_ms,
        )
        payload = await self._build_metrics_snapshot(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            limit=limit,
            from_ms=from_ms,
            to_ms=to_ms,
            window_name=window_name,
        )
        await self._publish_metrics_snapshot(payload)
        return payload["response"]

    async def provisional_candle_snapshot(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
    ) -> Dict[str, object]:
        now_ms = unix_ms()
        bucket_ms = timeframe_ms(timeframe)
        lookback_ms = max(
            bucket_ms + self.config.allowed_lateness_ms + 1_000,
            3_000,
        )
        from_ms = max(0, now_ms - lookback_ms)
        to_ms = now_ms + bucket_ms
        base_candles = await self.store.candle_snapshot(
            exchange,
            instrument_id,
            self.store.candle_limit,
        )
        provisional_candles = [
            candle.to_api()
            for candle in self.aggregator.provisional()
            if candle.exchange == exchange
            and candle.instrument_id == instrument_id
        ]
        live_seconds = [
            {
                **candle,
                "status": "provisional"
                if candle.get("status") == "provisional"
                else candle.get("status"),
            }
            for candle in [*base_candles, *provisional_candles]
            if int(candle["openTime"]) >= from_ms
            and int(candle["openTime"]) < to_ms
        ]

        if timeframe == "1s":
            values = [
                {**candle, "source": "provisional"}
                for candle in provisional_candles
                if int(candle["openTime"]) >= from_ms
            ]
        else:
            grouped: Dict[int, List[Dict[str, object]]] = {}
            for candle in live_seconds:
                bucket = (int(candle["openTime"]) // bucket_ms) * bucket_ms
                grouped.setdefault(bucket, []).append(candle)
            values = [
                self._aggregate_provisional_bucket(
                    sorted(
                        bucket_candles,
                        key=lambda item: int(item["openTime"]),
                    ),
                    timeframe=timeframe,
                    bucket_open_ms=bucket,
                    bucket_ms=bucket_ms,
                    now_ms=now_ms,
                )
                for bucket, bucket_candles in sorted(grouped.items())
            ]

        data_to = (
            max(int(candle["closeTime"]) for candle in values)
            if values
            else now_ms
        )
        response = {
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "source": "provisional",
            "generatedAt": now_ms,
            "revision": self.store.revision,
            "chartLatency": {
                "generatedAt": now_ms,
                "dataTo": data_to,
                "effectiveLagMs": max(0, now_ms - data_to),
                "stableDelayMs": 0,
                "allowedLatenessMs": self.config.allowed_lateness_ms,
            },
            "candles": values[-2:],
        }
        self.observability.observe_chart_snapshot(
            "provisional_candles_ws",
            response,
        )
        return response

    async def stable_candle_snapshot(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        limit: int,
    ) -> Dict[str, object]:
        now_ms = unix_ms()
        bucket_ms = timeframe_ms(timeframe)
        response_to = max(0, now_ms - self.stable_chart_delay_ms)
        response_to = (response_to // bucket_ms) * bucket_ms
        response_from = max(0, response_to - ((limit + 1) * bucket_ms))
        base_candles = await self.store.candle_snapshot(
            exchange,
            instrument_id,
            self.store.candle_limit,
        )
        page = aggregate_memory_candles(
            base_candles,
            timeframe=timeframe,
            from_ms=response_from,
            to_ms=response_to,
            limit=limit,
        )
        next_before = (
            page.candles[0]["openTime"]
            if page.candles and page.has_more
            else None
        )
        response = {
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "source": page.source,
            "from": response_from,
            "to": response_to,
            "count": len(page.candles),
            "hasMore": page.has_more,
            "nextBefore": next_before,
            "revision": self.stable_candle_revision,
            "chartLatency": {
                "generatedAt": now_ms,
                "dataTo": response_to,
                "effectiveLagMs": max(0, now_ms - response_to),
                "stableDelayMs": self.stable_chart_delay_ms,
                "allowedLatenessMs": self.config.allowed_lateness_ms,
            },
            "candles": page.candles,
        }
        self.observability.observe_chart_snapshot("stable_candles_ws", response)
        return response

    @staticmethod
    def _aggregate_provisional_bucket(
        candles: List[Dict[str, object]],
        *,
        timeframe: str,
        bucket_open_ms: int,
        bucket_ms: int,
        now_ms: int,
    ) -> Dict[str, object]:
        priced = [
            candle
            for candle in candles
            if all(
                candle.get(field) is not None
                for field in ("open", "high", "low", "close")
            )
        ]
        first = priced[0] if priced else None
        last = priced[-1] if priced else None
        high = (
            max(Decimal(str(candle["high"])) for candle in priced)
            if priced
            else None
        )
        low = (
            min(Decimal(str(candle["low"])) for candle in priced)
            if priced
            else None
        )
        base_volume = sum(
            (Decimal(str(candle["baseVolume"])) for candle in candles),
            Decimal("0"),
        )
        quote_volume = sum(
            (Decimal(str(candle["quoteVolume"])) for candle in candles),
            Decimal("0"),
        )
        return {
            "exchange": candles[0]["exchange"],
            "marketType": candles[0]["marketType"],
            "instrumentId": candles[0]["instrumentId"],
            "timeframe": timeframe,
            "openTime": bucket_open_ms,
            "closeTime": bucket_open_ms + bucket_ms,
            "open": first["open"] if first else None,
            "high": str(high) if high is not None else None,
            "low": str(low) if low is not None else None,
            "close": last["close"] if last else None,
            "baseVolume": str(base_volume),
            "quoteVolume": str(quote_volume),
            "tradeCount": sum(int(candle.get("tradeCount", 0)) for candle in candles),
            "status": "provisional",
            "revision": max(int(candle.get("revision", 1)) for candle in candles),
            "firstTradeId": first.get("firstTradeId") if first else None,
            "lastTradeId": last.get("lastTradeId") if last else None,
            "finalizedAt": now_ms,
            "source": "provisional",
        }

    async def _build_metrics_snapshot(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        limit: int,
        from_ms: Optional[int],
        to_ms: Optional[int],
        window_name: str,
    ) -> Dict[str, object]:
        started_at = unix_ms()
        history = await self.candle_history(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            limit=limit,
            from_ms=from_ms,
            to_ms=to_ms,
        )
        metrics = compute_metrics(
            history["candles"],
            timeframe=timeframe,
            event_limit=None,
        )
        all_events = metrics["events"]
        response_metrics = {
            **metrics,
            "events": all_events[:8],
        }
        correlations = await self._cached_cross_pair_correlations(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            window_name=window_name,
            limit=limit,
            from_ms=history["from"],
            to_ms=history["to"],
            target_candles=history["candles"],
        )
        finished_at = unix_ms()
        response = {
            "exchange": exchange,
            "marketType": self.config.market_type,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "source": history["source"],
            "from": history["from"],
            "to": history["to"],
            "hasMore": history["hasMore"],
            "nextBefore": history["nextBefore"],
            **response_metrics,
            "crossPairCorrelations": correlations,
            "metricsLatency": {
                "generatedAt": finished_at,
                "dataTo": history["to"],
                "effectiveLagMs": max(0, finished_at - int(history["to"])),
                "calculatedAt": finished_at,
                "computeDurationMs": max(0, finished_at - started_at),
                "windowName": window_name,
            },
        }
        self.observability.observe_metrics_snapshot(response)
        return {
            "response": response,
            "marketType": self.config.market_type,
            "windowName": window_name,
            "allEvents": all_events,
            "sourceCandles": history["candles"],
            "calculatedAt": finished_at,
            "computeDurationMs": max(0, finished_at - started_at),
        }

    async def _publish_metrics_snapshot(self, payload: Dict[str, object]) -> None:
        response = payload["response"]
        assert isinstance(response, dict)
        await self.database.enqueue_metrics(payload)
        window_name = str(payload["windowName"])
        if window_name == "custom":
            return
        scope = (
            str(response["exchange"]),
            str(response["instrumentId"]),
            str(response["timeframe"]),
            window_name,
        )
        self.metric_cache[scope] = response
        self.metric_revision += 1
        self.metric_scope_revisions[scope] = self.metric_revision
        self.computed_metric_snapshots += 1
        self.last_metric_error = None
        await self._notify_streams(metrics=True)

    def cached_metrics(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        window_name: str,
    ) -> Tuple[int, Optional[Dict[str, object]]]:
        scope = (exchange, instrument_id, timeframe, window_name)
        return (
            self.metric_scope_revisions.get(scope, -1),
            self.metric_cache.get(scope),
        )

    async def handle_connection_state(
        self,
        exchange: str,
        connected: bool,
        timestamp_ms: int,
    ) -> None:
        if not connected:
            self._disconnected_since.setdefault(exchange, timestamp_ms)
            return

        disconnected_since = self._disconnected_since.pop(exchange, None)
        if disconnected_since is None:
            return
        for instrument in self.config.subscriptions_for(exchange):
            self.aggregator.mark_gap(
                (
                    exchange,
                    self.config.market_type,
                    instrument.instrument_id,
                ),
                disconnected_since,
                timestamp_ms,
            )
        self._schedule_recovery(f"{exchange}-reconnect", [exchange])

    async def _consume_trades(self) -> None:
        while True:
            trade = await self.trade_queue.get()
            try:
                processed_at = unix_ms()
                self.observability.observe_trade(trade, processed_at)
                await self.store.apply_trade(trade)
                revised = self.aggregator.add_trade(
                    trade,
                    received_at_ms=trade.received_timestamp_ms,
                )
                notify_stable = False
                if revised is not None:
                    self.revised_candles += 1
                    await self.store.apply_candle(revised)
                    notify_stable = True
                await self._notify_streams(
                    market=True,
                    provisional=True,
                    stable=notify_stable,
                )
                await self.database.enqueue_trade(trade)
                if revised is not None:
                    await self.database.enqueue_candle(revised)
                    await self._schedule_metrics_for_candle(revised)
                self.processed_trades += 1
            finally:
                self.trade_queue.task_done()

    async def _finalize_candles(self) -> None:
        while True:
            now = unix_ms()
            finalized = self.aggregator.finalize_due(
                now,
                self._active_streams(),
            )
            for candle in finalized:
                await self.store.apply_candle(candle)
                await self.database.enqueue_candle(candle)
                await self._schedule_metrics_for_candle(candle)
            if finalized:
                await self._notify_streams(stable=True)
            await asyncio.sleep(0.1)

    async def _schedule_metrics_for_candle(self, candle: object) -> None:
        if getattr(candle, "timeframe", None) != "1s":
            return
        close_time_ms = int(getattr(candle, "close_time_ms"))
        recovered = getattr(candle, "status", None) == "recovered"
        for timeframe in TIMEFRAME_SECONDS:
            bucket_ms = timeframe_ms(timeframe)
            if timeframe != "1s" and not recovered and close_time_ms % bucket_ms:
                continue
            await self._enqueue_metric_scope(
                (
                    getattr(candle, "exchange"),
                    getattr(candle, "instrument_id"),
                    timeframe,
                    "default",
                )
            )
            if timeframe == METRICS_24H_TIMEFRAME:
                await self._enqueue_metric_scope(
                    (
                        getattr(candle, "exchange"),
                        getattr(candle, "instrument_id"),
                        timeframe,
                        "24h",
                    )
                )

    async def _wait_for_stream_revision(
        self,
        revision_name: str,
        last_revision: int,
        timeout: float,
    ) -> int:
        async with self._stream_condition:
            if getattr(self, revision_name) == last_revision:
                try:
                    await asyncio.wait_for(
                        self._stream_condition.wait_for(
                            lambda: getattr(self, revision_name) != last_revision
                        ),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    pass
            return int(getattr(self, revision_name))

    async def _notify_streams(
        self,
        *,
        market: bool = False,
        provisional: bool = False,
        stable: bool = False,
        metrics: bool = False,
    ) -> None:
        async with self._stream_condition:
            if market:
                self.market_stream_revision += 1
            if provisional:
                self.provisional_candle_revision += 1
            if stable:
                self.stable_candle_revision += 1
            if market or provisional or stable or metrics:
                self._stream_condition.notify_all()

    async def _enqueue_metric_scope(self, scope: MetricScope) -> None:
        if scope in self._pending_metric_scopes:
            return
        self._pending_metric_scopes.add(scope)
        try:
            self.metric_queue.put_nowait(scope)
        except asyncio.QueueFull:
            self._pending_metric_scopes.discard(scope)

    async def _process_metric_updates(self) -> None:
        while True:
            scope = await self.metric_queue.get()
            self._pending_metric_scopes.discard(scope)
            try:
                exchange, instrument_id, timeframe, window_name = scope
                options = self._metrics_window_options(
                    timeframe=timeframe,
                    window_name=window_name,
                )
                payload = await self._build_metrics_snapshot(
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    window_name=window_name,
                    **options,
                )
                await self._publish_metrics_snapshot(payload)
            except Exception as error:
                self.last_metric_error = str(error)
            finally:
                self.metric_queue.task_done()

    def _metrics_window_options(
        self,
        *,
        timeframe: str,
        window_name: str,
    ) -> Dict[str, Optional[int]]:
        if window_name == "24h":
            now_ms = unix_ms()
            return {
                "limit": METRICS_24H_LIMIT,
                "from_ms": now_ms - METRICS_24H_WINDOW_MS,
                "to_ms": now_ms,
            }
        return {
            "limit": METRICS_DEFAULT_LIMIT,
            "from_ms": None,
            "to_ms": None,
        }

    @staticmethod
    def _metrics_window_name(
        *,
        timeframe: str,
        limit: int,
        from_ms: Optional[int],
        to_ms: Optional[int],
    ) -> str:
        if (
            timeframe == METRICS_24H_TIMEFRAME
            and from_ms is not None
            and to_ms is not None
            and to_ms - from_ms <= METRICS_24H_WINDOW_MS + 60_000
            and limit >= METRICS_24H_LIMIT
        ):
            return "24h"
        if from_ms is None and to_ms is None and limit <= METRICS_DEFAULT_LIMIT:
            return "default"
        return "custom"

    def _active_streams(self) -> List[StreamKey]:
        streams: List[StreamKey] = []
        for exchange, collector in self.collectors.items():
            if not collector.connected:
                continue
            streams.extend(
                (
                    exchange,
                    self.config.market_type,
                    instrument.instrument_id,
                )
                for instrument in self.config.subscriptions_for(exchange)
                if collector.is_instrument_active(instrument.instrument_id)
            )
        return streams

    def record_frontend_display_latency(
        self,
        samples: Sequence[Mapping[str, object]],
    ) -> int:
        valid_samples: List[Mapping[str, object]] = []
        for sample in samples:
            exchange = str(sample.get("exchange") or "")
            instrument_id = str(sample.get("instrumentId") or "")
            instrument = self.config.instrument_by_id(instrument_id)
            if (
                exchange not in self.config.exchanges
                or instrument is None
                or exchange not in instrument.symbols
            ):
                continue
            valid_samples.append(sample)
        return self.observability.observe_frontend_display(
            valid_samples,
            unix_ms(),
        )

    def observability_snapshot(self) -> Dict[str, object]:
        return self.observability.snapshot(unix_ms())

    def prometheus_metrics(self) -> str:
        health = self.health(include_observability=False)
        return self.observability.prometheus_text(unix_ms()) + service_prometheus_text(
            collectors=health["collectors"],
            pipeline=health["pipeline"],
            metrics=health["metrics"],
            database=health["database"],
        )

    def health(self, include_observability: bool = True) -> Dict[str, object]:
        collectors = {
            name: collector.health()
            for name, collector in self.collectors.items()
        }
        connected_count = sum(
            1 for collector in self.collectors.values() if collector.connected
        )
        payload: Dict[str, object] = {
            "status": (
                "ok"
                if connected_count == len(self.collectors)
                else "degraded"
            ),
            "configVersion": self.config.config_version,
            "collectors": collectors,
            "pipeline": {
                "queueSize": self.trade_queue.qsize(),
                "queueCapacity": self.trade_queue.maxsize,
                "processedTrades": self.processed_trades,
                "revisedCandles": self.revised_candles,
            },
            "streams": {
                "marketRevision": self.market_stream_revision,
                "provisionalCandleRevision": self.provisional_candle_revision,
                "stableCandleRevision": self.stable_candle_revision,
                "metricRevision": self.metric_revision,
            },
            "metrics": {
                "queueSize": self.metric_queue.qsize(),
                "queueCapacity": self.metric_queue.maxsize,
                "pendingScopes": len(self._pending_metric_scopes),
                "computedSnapshots": self.computed_metric_snapshots,
                "cachedScopes": len(self.metric_cache),
                "cachedCorrelations": len(self.correlation_cache),
                "correlationRefreshMs": CORRELATION_REFRESH_MS,
                "lastError": self.last_metric_error,
            },
            "chart": {
                "stableDelayMs": self.stable_chart_delay_ms,
                "allowedLatenessMs": self.config.allowed_lateness_ms,
                "rawTradeTimeframes": sorted(RAW_TRADE_CHART_TIMEFRAMES),
                "rawTradeRetentionHours": self.config.raw_trade_retention_hours,
                "secondRepairHours": self.second_repair_hours,
                "binanceSecondBackfillHours": self.binance_second_backfill_hours,
            },
            "database": self.database.health(),
            "recovery": dict(self.recovery_status),
        }
        if include_observability:
            payload["observability"] = self.observability.health_summary()
        return payload

    async def _cross_pair_correlations(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        limit: int,
        from_ms: int,
        to_ms: int,
        target_candles: List[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        values: List[Dict[str, object]] = []
        peer_limit = min(limit, 500)
        for instrument in self.config.instruments:
            if instrument.instrument_id == instrument_id:
                continue
            if exchange not in instrument.symbols:
                continue
            try:
                peer_history = await self.candle_history(
                    exchange=exchange,
                    instrument_id=instrument.instrument_id,
                    timeframe=timeframe,
                    limit=peer_limit,
                    from_ms=from_ms,
                    to_ms=to_ms,
                )
            except Exception:
                continue
            correlation = compute_return_correlation(
                target_candles,
                peer_history["candles"],
            )
            if correlation is None:
                continue
            values.append(
                {
                    "instrumentId": instrument.instrument_id,
                    "name": instrument.name,
                    "base": instrument.base,
                    "correlation": correlation["correlation"],
                    "sampleSize": correlation["sampleSize"],
                    "source": peer_history["source"],
                }
            )
        return sorted(
            values,
            key=lambda item: abs(float(item["correlation"])),
            reverse=True,
        )

    async def _cached_cross_pair_correlations(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        window_name: str,
        limit: int,
        from_ms: int,
        to_ms: int,
        target_candles: List[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        now_ms = unix_ms()
        scope = (exchange, instrument_id, timeframe, window_name)
        cached = self.correlation_cache.get(scope)
        if (
            cached is not None
            and now_ms - int(cached["calculatedAt"]) < CORRELATION_REFRESH_MS
        ):
            return list(cached["values"])

        values = await self._cross_pair_correlations(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            limit=limit,
            from_ms=from_ms,
            to_ms=to_ms,
            target_candles=target_candles,
        )
        self.correlation_cache[scope] = {
            "calculatedAt": now_ms,
            "values": values,
        }
        return values

    def _schedule_recovery(self, reason: str, exchanges: Sequence[str]) -> None:
        if not self.recovery_enabled or not self.database.database_url:
            return
        if self._recovery_task is not None and not self._recovery_task.done():
            return
        self._recovery_task = asyncio.create_task(
            self._run_recovery(reason, exchanges),
            name="historical-recovery-backfill",
        )

    async def _run_recovery(self, reason: str, exchanges: Sequence[str]) -> None:
        async with self._recovery_lock:
            started_at = unix_ms()
            end_ms = align_closed_end_ms(None, RECOVERY_INTERVAL_MS["1m"])
            start_ms = max(
                0,
                end_ms - int(self.recovery_lookback_hours * 60 * 60 * 1000),
            )
            second_end_ms = max(
                0,
                ((started_at - self.stable_chart_delay_ms) // 1000) * 1000,
            )
            second_start_ms = max(
                0,
                second_end_ms - int(self.second_repair_hours * 60 * 60 * 1000),
            )
            historical_second_end_ms = align_closed_end_ms(
                started_at - self.stable_chart_delay_ms,
                RECOVERY_INTERVAL_MS["1s"],
            )
            historical_second_start_ms = max(
                0,
                historical_second_end_ms
                - int(self.binance_second_backfill_hours * 60 * 60 * 1000),
            )
            self.recovery_status.update(
                {
                    "running": True,
                    "lastReason": reason,
                    "lastStartedAt": started_at,
                    "lastFinishedAt": None,
                    "insertedCandles": 0,
                    "insertedHistoricalSecondCandles": 0,
                    "repairedSecondCandles": 0,
                    "failedMarkets": {},
                    "lastError": None,
                }
            )

            pool: Optional[asyncpg.Pool] = None
            total_inserted = 0
            total_inserted_seconds = 0
            total_repaired = 0
            failed_markets: Dict[str, str] = {}
            try:
                database_url = normalize_database_url(self.database.database_url)
                if database_url is None:
                    return
                pool = await asyncpg.create_pool(
                    dsn=database_url,
                    min_size=1,
                    max_size=2,
                )
                for exchange in exchanges:
                    for instrument in self.config.instruments:
                        if exchange not in instrument.symbols:
                            continue
                        market_key = f"{exchange}:{instrument.instrument_id}"
                        if (
                            exchange == "binance"
                            and self.binance_second_backfill_hours > 0
                            and historical_second_end_ms
                            > historical_second_start_ms
                        ):
                            try:
                                total_inserted_seconds += await backfill_market(
                                    pool=pool,
                                    exchange=exchange,
                                    market_type=self.config.market_type,
                                    instrument=instrument,
                                    timeframe="1s",
                                    start_ms=historical_second_start_ms,
                                    end_ms=historical_second_end_ms,
                                    limit=RECOVERY_REQUEST_LIMIT,
                                    batch_size=5000,
                                    request_sleep=0.01,
                                    max_retries=2,
                                    dry_run=False,
                                )
                                self.recovery_status[
                                    "insertedHistoricalSecondCandles"
                                ] = total_inserted_seconds
                            except Exception as error:
                                failed_markets[
                                    f"binance-1s-backfill:{market_key}"
                                ] = str(error)
                        if (
                            self.second_repair_hours > 0
                            and second_end_ms > second_start_ms
                        ):
                            try:
                                repaired_count = await (
                                    self.database.repair_one_second_candles_from_raw_trades
                                )(
                                    exchange=exchange,
                                    market_type=self.config.market_type,
                                    instrument_id=instrument.instrument_id,
                                    from_ms=second_start_ms,
                                    to_ms=second_end_ms,
                                )
                                total_repaired += repaired_count
                                self.recovery_status[
                                    "repairedSecondCandles"
                                ] = total_repaired
                            except Exception as error:
                                failed_markets[
                                    f"1s-repair:{market_key}"
                                ] = str(error)
                        try:
                            total_inserted += await backfill_market(
                                pool=pool,
                                exchange=exchange,
                                market_type=self.config.market_type,
                                instrument=instrument,
                                timeframe="1m",
                                start_ms=start_ms,
                                end_ms=end_ms,
                                limit=RECOVERY_REQUEST_LIMIT,
                                batch_size=1000,
                                request_sleep=0.01,
                                max_retries=2,
                                dry_run=False,
                            )
                            self.recovery_status["insertedCandles"] = total_inserted
                        except Exception as error:
                            failed_markets[f"1m-backfill:{market_key}"] = str(error)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.recovery_status["lastError"] = str(error)
            finally:
                if pool is not None:
                    await pool.close()
                self.recovery_status.update(
                    {
                        "running": False,
                        "lastFinishedAt": unix_ms(),
                        "insertedCandles": total_inserted,
                        "insertedHistoricalSecondCandles": total_inserted_seconds,
                        "repairedSecondCandles": total_repaired,
                        "failedMarkets": failed_markets,
                    }
                )


def parse_recovery_lookback_hours(value: Optional[str]) -> float:
    if value is None:
        return 72.0
    normalized = value.strip().lower()
    if not normalized:
        return 72.0

    suffixes = {
        "hours": 1.0,
        "hour": 1.0,
        "hrs": 1.0,
        "hr": 1.0,
        "h": 1.0,
        "days": 24.0,
        "day": 24.0,
        "d": 24.0,
    }
    for suffix, multiplier in suffixes.items():
        if normalized.endswith(suffix):
            number = normalized[: -len(suffix)].strip()
            if not number:
                raise ValueError(
                    "TICKFRAME_RECOVERY_BACKFILL_HOURS must include a number"
                )
            return float(number) * multiplier

    return float(normalized)


def parse_duration_ms(value: Optional[str], default_ms: int) -> int:
    if value is None:
        return default_ms
    normalized = value.strip().lower()
    if not normalized:
        return default_ms

    suffixes = (
        ("milliseconds", 1.0),
        ("millisecond", 1.0),
        ("msecs", 1.0),
        ("msec", 1.0),
        ("ms", 1.0),
        ("seconds", 1000.0),
        ("second", 1000.0),
        ("secs", 1000.0),
        ("sec", 1000.0),
        ("s", 1000.0),
        ("minutes", 60_000.0),
        ("minute", 60_000.0),
        ("mins", 60_000.0),
        ("min", 60_000.0),
        ("m", 60_000.0),
    )
    for suffix, multiplier in suffixes:
        if normalized.endswith(suffix):
            number = normalized[: -len(suffix)].strip()
            if not number:
                raise ValueError("duration must include a number")
            return max(0, int(float(number) * multiplier))

    return max(0, int(float(normalized)))
