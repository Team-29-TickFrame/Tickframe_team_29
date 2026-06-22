import asyncio
import os
import time
from typing import Dict, List, Optional, Sequence, Tuple

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
from .history import aggregate_memory_candles, resolve_time_range, timeframe_ms
from .metrics import compute_metrics, compute_return_correlation
from .models import Trade
from .store import LiveStore


def unix_ms() -> int:
    return int(time.time() * 1000)


RAW_TRADE_CHART_TIMEFRAMES = {"1s", "5s", "15s"}
DEFAULT_STABLE_CHART_DELAY_MS = 10_000
DEFAULT_SECOND_REPAIR_HOURS = 72.0
DEFAULT_BINANCE_SECOND_BACKFILL_HOURS = 24.0


class MarketDataService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = LiveStore(config)
        self.database = DatabaseWriter()
        self.aggregator = CandleAggregator(
            allowed_lateness_ms=config.allowed_lateness_ms
        )
        self.trade_queue: "asyncio.Queue[Trade]" = asyncio.Queue(maxsize=200_000)
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

    async def start(self) -> None:
        await self.database.start()
        self._tasks = [
            asyncio.create_task(self._consume_trades(), name="trade-consumer"),
            asyncio.create_task(self._finalize_candles(), name="candle-finalizer"),
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
        return {
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "source": page.source,
            "from": response_from,
            "to": response_to,
            "count": len(page.candles),
            "hasMore": page.has_more,
            "nextBefore": next_before,
            "candles": page.candles,
        }

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
        )
        correlations = await self._cross_pair_correlations(
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            limit=limit,
            from_ms=history["from"],
            to_ms=history["to"],
            target_candles=history["candles"],
        )
        return {
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "source": history["source"],
            "from": history["from"],
            "to": history["to"],
            "hasMore": history["hasMore"],
            "nextBefore": history["nextBefore"],
            **metrics,
            "crossPairCorrelations": correlations,
        }

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
                await self.store.apply_trade(trade)
                revised = self.aggregator.add_trade(
                    trade,
                    received_at_ms=trade.received_timestamp_ms,
                )
                await self.database.enqueue_trade(trade)
                if revised is not None:
                    self.revised_candles += 1
                    await self.store.apply_candle(revised)
                    await self.database.enqueue_candle(revised)
                self.processed_trades += 1
            finally:
                self.trade_queue.task_done()

    async def _finalize_candles(self) -> None:
        while True:
            now = unix_ms()
            for candle in self.aggregator.finalize_due(
                now,
                self._active_streams(),
            ):
                await self.store.apply_candle(candle)
                await self.database.enqueue_candle(candle)
            await asyncio.sleep(0.1)

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

    def health(self) -> Dict[str, object]:
        collectors = {
            name: collector.health()
            for name, collector in self.collectors.items()
        }
        connected_count = sum(
            1 for collector in self.collectors.values() if collector.connected
        )
        return {
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
            "chart": {
                "stableDelayMs": self.stable_chart_delay_ms,
                "rawTradeTimeframes": sorted(RAW_TRADE_CHART_TIMEFRAMES),
                "rawTradeRetentionHours": self.config.raw_trade_retention_hours,
                "secondRepairHours": self.second_repair_hours,
                "binanceSecondBackfillHours": self.binance_second_backfill_hours,
            },
            "database": self.database.health(),
            "recovery": dict(self.recovery_status),
        }

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
