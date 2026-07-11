from datetime import datetime, timezone
from decimal import Decimal
import asyncio
import unittest
from unittest.mock import AsyncMock

from backend.app.database import DatabaseWriter


def at_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


class RawTradeHistoryTests(unittest.TestCase):
    def test_raw_trade_rollup_fills_quiet_seconds_from_previous_close(self) -> None:
        rows = [
            {
                "open_time": at_ms(1_000),
                "open": Decimal("100"),
                "high": Decimal("102"),
                "low": Decimal("99"),
                "close": Decimal("101"),
                "base_volume": Decimal("0.5"),
                "quote_volume": Decimal("50.5"),
                "trade_count": 3,
                "first_trade_id": "a",
                "last_trade_id": "c",
                "finalized_at": at_ms(1_900),
            },
            {
                "open_time": at_ms(3_000),
                "open": Decimal("102"),
                "high": Decimal("104"),
                "low": Decimal("101"),
                "close": Decimal("103"),
                "base_volume": Decimal("0.7"),
                "quote_volume": Decimal("72.1"),
                "trade_count": 2,
                "first_trade_id": "d",
                "last_trade_id": "e",
                "finalized_at": at_ms(3_900),
            },
        ]

        page = DatabaseWriter._raw_trade_rows_to_history_page(
            rows,
            exchange="binance",
            market_type="spot",
            instrument_id="BTC-USDT",
            timeframe="1s",
            from_ms=0,
            to_ms=5_000,
            limit=10,
            previous_close=Decimal("99"),
        )

        self.assertEqual(page.source, "raw_trades")
        self.assertEqual(
            [candle["openTime"] for candle in page.candles],
            [0, 1_000, 2_000, 3_000, 4_000],
        )
        self.assertEqual(
            [candle["status"] for candle in page.candles],
            [
                "complete_empty",
                "complete",
                "complete_empty",
                "complete",
                "complete_empty",
            ],
        )
        self.assertEqual(page.candles[0]["close"], "99")
        self.assertEqual(page.candles[2]["close"], "101")
        self.assertEqual(page.candles[4]["close"], "103")
        self.assertEqual(page.candles[2]["tradeCount"], 0)
        self.assertEqual(page.candles[3]["tradeCount"], 2)

    def test_raw_trade_rollup_trims_to_latest_limit(self) -> None:
        page = DatabaseWriter._raw_trade_rows_to_history_page(
            [],
            exchange="binance",
            market_type="spot",
            instrument_id="BTC-USDT",
            timeframe="1s",
            from_ms=0,
            to_ms=5_000,
            limit=3,
            previous_close=Decimal("10"),
        )

        self.assertTrue(page.has_more)
        self.assertEqual(
            [candle["openTime"] for candle in page.candles],
            [2_000, 3_000, 4_000],
        )


class RawTradeRepairTests(unittest.IsolatedAsyncioTestCase):
    async def test_repair_is_noop_without_database_engine(self) -> None:
        writer = DatabaseWriter(database_url=None)

        repaired = await writer.repair_one_second_candles_from_raw_trades(
            exchange="binance",
            market_type="spot",
            instrument_id="BTC-USDT",
            from_ms=0,
            to_ms=60_000,
        )

        self.assertEqual(repaired, 0)


class DatabaseWriterLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_does_not_hang_when_database_keeps_failing(self) -> None:
        class FakeEngine:
            def __init__(self) -> None:
                self.dispose = AsyncMock()

        writer = DatabaseWriter(
            database_url="postgresql+asyncpg://unused",
            shutdown_timeout_seconds=0.01,
        )
        writer.engine = FakeEngine()  # type: ignore[assignment]
        writer._accepting_events = True
        writer._write_batch = AsyncMock(side_effect=RuntimeError("database down"))
        writer._task = asyncio.create_task(writer._run())
        await writer.queue.put(("metrics", {}))
        await asyncio.sleep(0)

        with self.assertLogs("backend.app.database", level="ERROR"):
            await asyncio.wait_for(writer.stop(), timeout=0.5)

        self.assertIsNone(writer._task)
        self.assertIsNone(writer.engine)
        self.assertGreaterEqual(writer.dropped_events, 1)
        self.assertIn("timed out", writer.last_error)

    async def test_enqueue_rejects_events_when_writer_task_is_dead(self) -> None:
        writer = DatabaseWriter(database_url="postgresql+asyncpg://unused")
        writer.engine = object()  # type: ignore[assignment]
        writer._accepting_events = True

        await writer.enqueue_metrics({})

        self.assertEqual(writer.queue.qsize(), 0)
        self.assertEqual(writer.dropped_events, 1)

    async def test_invalid_batch_is_dropped_without_poisoning_writer(self) -> None:
        writer = DatabaseWriter(database_url="postgresql+asyncpg://unused")
        writer._write_batch = AsyncMock(side_effect=ValueError("invalid payload"))
        writer._task = asyncio.create_task(writer._run())
        await writer.queue.put(("metrics", {}))

        with self.assertLogs("backend.app.database", level="ERROR"):
            await asyncio.wait_for(writer.queue.join(), timeout=0.5)

        self.assertFalse(writer._task.done())
        self.assertEqual(writer.dropped_events, 1)
        self.assertIn("Discarded invalid database batch", writer.last_error)
        writer._task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await writer._task


class HistorySourceTests(unittest.TestCase):
    def test_history_page_source_prioritizes_explicit_proxy(self) -> None:
        self.assertEqual(
            DatabaseWriter._history_page_source(
                [
                    {"history_source": "timescaledb"},
                    {"history_source": "binance_proxy_1s"},
                ]
            ),
            "binance_proxy_1s",
        )
        self.assertEqual(
            DatabaseWriter._history_page_source(
                [{"history_source": "historical_candles"}]
            ),
            "historical_candles",
        )
        self.assertEqual(DatabaseWriter._history_page_source([]), "timescaledb")


if __name__ == "__main__":
    unittest.main()
