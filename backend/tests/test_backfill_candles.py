import os
import unittest
from typing import Optional

from backend.scripts.backfill_candles import (
    INTERVAL_MS,
    align_closed_end_ms,
    binance_base_urls,
    bybit_interval,
    bybit_base_urls,
    parse_binance_klines,
    parse_bybit_klines,
    supports_rest_timeframe,
)


class BackfillCandleParserTests(unittest.TestCase):
    def test_binance_kline_is_mapped_to_historical_candle(self) -> None:
        values = parse_binance_klines(
            [
                [
                    60_000,
                    "100.0",
                    "110.0",
                    "90.0",
                    "105.0",
                    "2.5",
                    119_999,
                    "262.5",
                    42,
                ]
            ],
            market_type="spot",
            instrument_id="BTC-USDT",
            source_symbol="BTCUSDT",
            timeframe="1m",
        )

        self.assertEqual(len(values), 1)
        value = values[0]
        self.assertEqual(value.exchange, "binance")
        self.assertEqual(value.open_time_ms, 60_000)
        self.assertEqual(value.close_time_ms, 120_000)
        self.assertEqual(value.close, "105.0")
        self.assertEqual(value.quote_volume, "262.5")
        self.assertEqual(value.trade_count, 42)
        self.assertEqual(value.status, "complete")

    def test_binance_one_second_kline_is_supported(self) -> None:
        values = parse_binance_klines(
            [
                [
                    60_000,
                    "100.0",
                    "110.0",
                    "90.0",
                    "105.0",
                    "2.5",
                    60_999,
                    "262.5",
                    42,
                ]
            ],
            market_type="spot",
            instrument_id="BTC-USDT",
            source_symbol="BTCUSDT",
            timeframe="1s",
        )

        self.assertEqual(INTERVAL_MS["1s"], 1000)
        self.assertEqual(values[0].close_time_ms, 61_000)
        self.assertEqual(values[0].timeframe, "1s")

    def test_bybit_kline_is_sorted_and_mapped_to_historical_candle(self) -> None:
        values = parse_bybit_klines(
            {
                "retCode": 0,
                "result": {
                    "list": [
                        ["120000", "105", "115", "100", "110", "3", "330"],
                        ["60000", "100", "110", "90", "105", "2", "210"],
                    ]
                },
            },
            market_type="spot",
            instrument_id="BTC-USDT",
            source_symbol="BTCUSDT",
            timeframe="1m",
        )

        self.assertEqual([value.open_time_ms for value in values], [60_000, 120_000])
        self.assertEqual(values[0].exchange, "bybit")
        self.assertEqual(values[0].base_volume, "2")
        self.assertEqual(values[0].quote_volume, "210")
        self.assertEqual(values[0].trade_count, 0)
        self.assertEqual(values[0].status, "complete")

    def test_end_time_is_aligned_to_closed_interval(self) -> None:
        self.assertEqual(align_closed_end_ms(125_123, 60_000), 120_000)

    def test_bybit_one_second_rest_kline_is_not_supported(self) -> None:
        self.assertFalse(supports_rest_timeframe("bybit", "1s"))
        self.assertTrue(supports_rest_timeframe("binance", "1s"))
        with self.assertRaises(ValueError):
            bybit_interval("1s")

    def test_rest_base_urls_can_be_overridden(self) -> None:
        with temporary_env(
            TICKFRAME_BINANCE_REST_URLS="https://binance-one.test, https://binance-two.test",
            TICKFRAME_BYBIT_REST_URLS="https://bybit-one.test, https://bybit-two.test",
        ):
            self.assertEqual(
                tuple(binance_base_urls()),
                ("https://binance-one.test", "https://binance-two.test"),
            )
            self.assertEqual(
                tuple(bybit_base_urls()),
                ("https://bybit-one.test", "https://bybit-two.test"),
            )


class temporary_env:
    def __init__(self, **values: Optional[str]) -> None:
        self.values = values
        self.previous: dict[str, Optional[str]] = {}

    def __enter__(self) -> None:
        for name, value in self.values.items():
            self.previous[name] = os.environ.get(name)
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def __exit__(self, *args: object) -> None:
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
