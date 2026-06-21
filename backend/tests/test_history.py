import unittest

from backend.app.history import (
    aggregate_memory_candles,
    resolve_time_range,
)


def candle(
    second: int,
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
    volume: str = "1",
    trades: int = 1,
    status: str = "complete",
    revision: int = 1,
) -> dict:
    open_time = second * 1000
    return {
        "exchange": "binance",
        "marketType": "spot",
        "instrumentId": "BTC-USDT",
        "timeframe": "1s",
        "openTime": open_time,
        "closeTime": open_time + 1000,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "baseVolume": volume,
        "quoteVolume": volume,
        "tradeCount": trades,
        "status": status,
        "revision": revision,
        "firstTradeId": str(second),
        "lastTradeId": str(second),
        "finalizedAt": open_time + 3000,
    }


class HistoryTests(unittest.TestCase):
    def test_memory_rollup_uses_first_last_and_exact_sums(self) -> None:
        values = [
            candle(
                second,
                open_price=str(100 + second),
                high=str(102 + second),
                low=str(99 + second),
                close=str(101 + second),
                volume="0.1",
                trades=2,
            )
            for second in range(5)
        ]

        page = aggregate_memory_candles(
            values,
            timeframe="5s",
            from_ms=0,
            to_ms=5000,
            limit=10,
        )

        self.assertEqual(len(page.candles), 1)
        value = page.candles[0]
        self.assertEqual(value["open"], "100")
        self.assertEqual(value["high"], "106")
        self.assertEqual(value["low"], "99")
        self.assertEqual(value["close"], "105")
        self.assertEqual(value["baseVolume"], "0.5")
        self.assertEqual(value["tradeCount"], 10)
        self.assertEqual(value["status"], "complete")

    def test_missing_source_second_marks_rollup_incomplete(self) -> None:
        values = [
            candle(
                second,
                open_price="1",
                high="1",
                low="1",
                close="1",
            )
            for second in range(4)
        ]
        page = aggregate_memory_candles(
            values,
            timeframe="5s",
            from_ms=0,
            to_ms=5000,
            limit=10,
        )
        self.assertEqual(page.candles[0]["status"], "incomplete")

    def test_incomplete_source_candle_keeps_visible_ohlc_but_status(self) -> None:
        values = [
            candle(
                second,
                open_price="1",
                high="2",
                low="0.5",
                close="1.5",
                status="incomplete" if second == 2 else "complete",
            )
            for second in range(5)
        ]
        page = aggregate_memory_candles(
            values,
            timeframe="5s",
            from_ms=0,
            to_ms=5000,
            limit=10,
        )
        self.assertEqual(page.candles[0]["status"], "incomplete")
        self.assertEqual(page.candles[0]["open"], "1")
        self.assertEqual(page.candles[0]["close"], "1.5")

    def test_history_page_returns_latest_values_and_has_more(self) -> None:
        values = [
            candle(
                second,
                open_price="1",
                high="1",
                low="1",
                close="1",
            )
            for second in range(10)
        ]
        page = aggregate_memory_candles(
            values,
            timeframe="1s",
            from_ms=0,
            to_ms=10_000,
            limit=3,
        )
        self.assertTrue(page.has_more)
        self.assertEqual(
            [value["openTime"] for value in page.candles],
            [7000, 8000, 9000],
        )

    def test_second_history_defaults_to_retention_window(self) -> None:
        from_ms, to_ms = resolve_time_range(
            timeframe="1s",
            limit=100,
            now_ms=2_000_000_000,
            from_ms=None,
            to_ms=None,
        )
        self.assertEqual(from_ms % 1000, 0)
        self.assertGreater(to_ms, from_ms)
        self.assertEqual(to_ms - from_ms, 14 * 24 * 60 * 60 * 1000)

    def test_persistent_history_has_unbounded_default_start(self) -> None:
        from_ms, _ = resolve_time_range(
            timeframe="1h",
            limit=100,
            now_ms=2_000_000_000,
            from_ms=None,
            to_ms=None,
        )
        self.assertEqual(from_ms, 0)

    def test_invalid_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_time_range(
                timeframe="1m",
                limit=100,
                now_ms=1000,
                from_ms=5000,
                to_ms=5000,
            )


if __name__ == "__main__":
    unittest.main()
