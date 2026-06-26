from decimal import Decimal
import unittest
from unittest.mock import patch

from backend.app.config import load_config
from backend.app.history import HistoryPage
from backend.app.models import Candle
from backend.app.service import (
    MarketDataService,
    parse_duration_ms,
    parse_recovery_lookback_hours,
)


class ServiceHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        service = MarketDataService(load_config())
        for second in range(5):
            await service.store.apply_candle(
                Candle(
                    exchange="binance",
                    market_type="spot",
                    instrument_id="BTC-USDT",
                    timeframe="1s",
                    open_time_ms=second * 1000,
                    close_time_ms=(second + 1) * 1000,
                    open=Decimal("100"),
                    high=Decimal("101"),
                    low=Decimal("99"),
                    close=Decimal("100"),
                    base_volume=Decimal("1"),
                    quote_volume=Decimal("100"),
                    trade_count=1,
                    status="complete",
                    revision=1,
                    first_trade_id=str(second),
                    last_trade_id=str(second),
                    finalized_at_ms=(second + 3) * 1000,
                )
            )
        self.service = service

    async def test_history_falls_back_to_memory_without_database(self) -> None:
        response = await self.service.candle_history(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="5s",
            limit=10,
            from_ms=0,
            to_ms=5000,
        )

        self.assertEqual(response["source"], "memory")
        self.assertEqual(response["count"], 1)
        self.assertEqual(response["candles"][0]["status"], "complete")
        self.assertEqual(response["candles"][0]["tradeCount"], 5)

    async def test_metrics_reuse_history_fallback_without_database(self) -> None:
        response = await self.service.metrics_snapshot(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1s",
            limit=30,
            from_ms=0,
            to_ms=5000,
        )

        self.assertEqual(response["source"], "memory")
        self.assertEqual(response["version"], "metrics-v3")
        self.assertEqual(response["count"], 5)
        self.assertEqual(response["latest"]["close"], 100.0)

    async def test_stable_candle_snapshot_uses_memory_window(self) -> None:
        self.service.stable_chart_delay_ms = 2_000

        with patch("backend.app.service.unix_ms", return_value=8_000):
            response = await self.service.stable_candle_snapshot(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1s",
                limit=3,
            )

        self.assertEqual(response["source"], "memory")
        self.assertEqual(response["to"], 6_000)
        self.assertEqual(response["chartLatency"]["effectiveLagMs"], 2_000)
        self.assertEqual(
            [candle["openTime"] for candle in response["candles"]],
            [2_000, 3_000, 4_000],
        )

    async def test_metrics_snapshot_includes_cross_pair_correlations(self) -> None:
        service = MarketDataService(load_config())
        for second in range(8):
            btc_price = Decimal(str(100 + second))
            eth_price = Decimal(str(200 + 2 * second))
            for instrument_id, price in (
                ("BTC-USDT", btc_price),
                ("ETH-USDT", eth_price),
            ):
                await service.store.apply_candle(
                    Candle(
                        exchange="binance",
                        market_type="spot",
                        instrument_id=instrument_id,
                        timeframe="1s",
                        open_time_ms=second * 1000,
                        close_time_ms=(second + 1) * 1000,
                        open=price,
                        high=price,
                        low=price,
                        close=price,
                        base_volume=Decimal("1"),
                        quote_volume=price,
                        trade_count=1,
                        status="complete",
                        revision=1,
                        first_trade_id=f"{instrument_id}:{second}",
                        last_trade_id=f"{instrument_id}:{second}",
                        finalized_at_ms=(second + 3) * 1000,
                    )
                )

        response = await service.metrics_snapshot(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1s",
            limit=20,
            from_ms=0,
            to_ms=8000,
        )

        correlations = response["crossPairCorrelations"]
        self.assertEqual(correlations[0]["instrumentId"], "ETH-USDT")
        self.assertGreater(correlations[0]["correlation"], 0.99)
        self.assertEqual(correlations[0]["sampleSize"], 7)

    async def test_recent_short_timeframes_prefer_delayed_raw_trade_history(
        self,
    ) -> None:
        class FakeDatabase:
            def __init__(self) -> None:
                self.raw_params = None

            async def raw_trade_candle_history(self, **params):
                self.raw_params = params
                return HistoryPage(
                    candles=[
                        {
                            "openTime": 89_000,
                            "closeTime": 90_000,
                            "open": "100",
                            "high": "101",
                            "low": "99",
                            "close": "100",
                        }
                    ],
                    has_more=False,
                    source="raw_trades",
                )

            async def candle_history(self, **_params):
                raise AssertionError("stored candle history should not be used")

        fake_database = FakeDatabase()
        self.service.database = fake_database  # type: ignore[assignment]
        self.service.stable_chart_delay_ms = 10_000

        with patch("backend.app.service.unix_ms", return_value=100_000):
            response = await self.service.candle_history(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1s",
                limit=5,
                from_ms=None,
                to_ms=None,
            )

        self.assertEqual(response["source"], "raw_trades")
        self.assertEqual(response["to"], 90_000)
        self.assertEqual(fake_database.raw_params["to_ms"], 90_000)
        self.assertEqual(fake_database.raw_params["from_ms"], 84_000)

    async def test_historical_second_source_skips_raw_trade_fallback(self) -> None:
        class FakeDatabase:
            def __init__(self) -> None:
                self.raw_called = False

            async def candle_history(self, **_params):
                return HistoryPage(
                    candles=[
                        {
                            "openTime": 89_000,
                            "closeTime": 90_000,
                            "open": "100",
                            "high": "101",
                            "low": "99",
                            "close": "100",
                        }
                    ],
                    has_more=False,
                    source="historical_candles",
                )

            async def raw_trade_candle_history(self, **_params):
                self.raw_called = True
                return None

        fake_database = FakeDatabase()
        self.service.database = fake_database  # type: ignore[assignment]

        with patch("backend.app.service.unix_ms", return_value=100_000):
            response = await self.service.candle_history(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1s",
                limit=5,
                from_ms=None,
                to_ms=None,
            )

        self.assertEqual(response["source"], "historical_candles")
        self.assertFalse(fake_database.raw_called)

    async def test_second_repair_window_is_capped_by_raw_retention(self) -> None:
        with patch.dict(
            "os.environ",
            {"TICKFRAME_SECOND_REPAIR_HOURS": "12d"},
        ):
            service = MarketDataService(load_config())

        self.assertEqual(service.second_repair_hours, 72.0)


class RecoveryConfigTests(unittest.TestCase):
    def test_recovery_lookback_accepts_hours_and_days(self) -> None:
        self.assertEqual(parse_recovery_lookback_hours(None), 72.0)
        self.assertEqual(parse_recovery_lookback_hours("288"), 288.0)
        self.assertEqual(parse_recovery_lookback_hours("288h"), 288.0)
        self.assertEqual(parse_recovery_lookback_hours("12d"), 288.0)
        self.assertEqual(parse_recovery_lookback_hours("12 days"), 288.0)


class DurationConfigTests(unittest.TestCase):
    def test_duration_parser_accepts_ms_seconds_and_minutes(self) -> None:
        self.assertEqual(parse_duration_ms(None, 10_000), 10_000)
        self.assertEqual(parse_duration_ms("", 10_000), 10_000)
        self.assertEqual(parse_duration_ms("15000", 10_000), 15_000)
        self.assertEqual(parse_duration_ms("15s", 10_000), 15_000)
        self.assertEqual(parse_duration_ms("0.5 min", 10_000), 30_000)


if __name__ == "__main__":
    unittest.main()
