import unittest
from decimal import Decimal
from typing import Optional

from backend.app.metrics import compute_metrics, compute_return_correlation


def candle(
    second: int,
    *,
    close: str,
    open_price: Optional[str] = None,
    high: Optional[str] = None,
    low: Optional[str] = None,
    volume: str = "1",
    quote_volume: Optional[str] = None,
    status: str = "complete",
) -> dict:
    open_time = second * 1000
    open_value = open_price if open_price is not None else close
    high_value = high if high is not None else close
    low_value = low if low is not None else close
    quote = (
        quote_volume
        if quote_volume is not None
        else str(Decimal(close) * Decimal(volume))
    )
    return {
        "exchange": "binance",
        "marketType": "spot",
        "instrumentId": "BTC-USDT",
        "timeframe": "1s",
        "openTime": open_time,
        "closeTime": open_time + 1000,
        "open": open_value,
        "high": high_value,
        "low": low_value,
        "close": close,
        "baseVolume": volume,
        "quoteVolume": quote,
        "tradeCount": 1,
        "status": status,
        "revision": 1,
        "firstTradeId": str(second),
        "lastTradeId": str(second),
        "finalizedAt": open_time + 3000,
    }


class MetricsTests(unittest.TestCase):
    def test_cumulative_vwap_and_deviation_are_deterministic(self) -> None:
        result = compute_metrics(
            [
                candle(0, close="100", volume="1"),
                candle(1, close="110", volume="2"),
                candle(2, close="120", volume="1"),
            ],
            timeframe="1s",
        )

        latest = result["latest"]
        self.assertEqual(result["version"], "metrics-v3")
        self.assertEqual(result["count"], 3)
        self.assertAlmostEqual(latest["vwap"], 110.0)
        self.assertAlmostEqual(latest["vwapDeviationPct"], 9.090909)
        self.assertEqual(result["summary"]["tradeCount"], 3)
        self.assertAlmostEqual(result["summary"]["baseVolume"], 4.0)
        self.assertAlmostEqual(result["summary"]["high"], 120.0)
        self.assertAlmostEqual(result["summary"]["low"], 100.0)

    def test_rsi_momentum_and_realized_volatility_use_rolling_windows(self) -> None:
        result = compute_metrics(
            [candle(second, close=str(100 + second)) for second in range(21)],
            timeframe="1s",
        )

        latest = result["latest"]
        self.assertEqual(latest["rsi"], 100.0)
        self.assertIsNotNone(latest["shortMomentumPct"])
        self.assertAlmostEqual(latest["momentumPct"], 13.207547)
        self.assertIsNotNone(latest["realizedVolatilityPct"])
        self.assertGreater(latest["realizedVolatilityPct"], 0)

    def test_range_volatility_and_mean_reversion_metrics_are_calculated(self) -> None:
        result = compute_metrics(
            [
                candle(
                    second,
                    open_price=str(99 + second),
                    high=str(102 + second),
                    low=str(98 + second),
                    close=str(100 + second),
                )
                for second in range(21)
            ],
            timeframe="1s",
        )

        latest = result["latest"]
        self.assertIsNotNone(latest["parkinsonVolatilityPct"])
        self.assertIsNotNone(latest["garmanKlassVolatilityPct"])
        self.assertIsNotNone(latest["meanReversionZScore"])
        self.assertIsNotNone(latest["distanceToMeanPct"])

    def test_volume_spike_produces_metric_event(self) -> None:
        values = [candle(second, close="100", volume="1") for second in range(20)]
        values.append(candle(20, close="100", volume="5"))

        result = compute_metrics(values, timeframe="1s")

        latest = result["latest"]
        self.assertEqual(latest["volumeSpikeRatio"], 5.0)
        self.assertEqual(result["events"][0]["type"], "volume_spike")
        self.assertEqual(result["events"][0]["severity"], "high")

    def test_null_close_keeps_point_but_skips_derived_values(self) -> None:
        value = candle(0, close="100")
        value["close"] = None
        value["open"] = None
        value["high"] = None
        value["low"] = None

        result = compute_metrics([value], timeframe="1s")

        self.assertEqual(result["count"], 1)
        self.assertIsNone(result["latest"]["close"])
        self.assertIsNone(result["latest"]["vwapDeviationPct"])
        self.assertEqual(result["events"], [])

    def test_double_top_pattern_generates_event(self) -> None:
        closes = [
            "100",
            "103",
            "107",
            "104",
            "101",
            "104",
            "107.2",
            "103",
            "99",
            "98",
            "97",
            "96",
        ]

        result = compute_metrics(
            [candle(second, close=close) for second, close in enumerate(closes)],
            timeframe="1s",
        )

        event_types = {event["type"] for event in result["events"]}
        self.assertIn("double_top", event_types)

    def test_bullish_rsi_divergence_generates_event(self) -> None:
        closes = [
            "100",
            "99",
            "98",
            "97",
            "96",
            "95",
            "94",
            "93",
            "92",
            "91",
            "90",
            "89",
            "88",
            "87",
            "86",
            "92",
            "96",
            "99",
            "97",
            "95",
            "93",
            "91",
            "89",
            "87",
            "85.5",
            "87",
            "89",
            "92",
        ]

        result = compute_metrics(
            [candle(second, close=close) for second, close in enumerate(closes)],
            timeframe="1s",
        )

        event_types = {event["type"] for event in result["events"]}
        self.assertIn("bullish_rsi_divergence", event_types)

    def test_price_volume_divergence_generates_event(self) -> None:
        values = [
            candle(second, close=str(100 + second), volume="10") for second in range(15)
        ]
        values.extend(
            [
                candle(15, close="116", volume="3"),
                candle(16, close="117", volume="2"),
                candle(17, close="118", volume="1"),
            ]
        )

        result = compute_metrics(values, timeframe="1s")

        event_types = {event["type"] for event in result["events"]}
        self.assertIn("price_volume_divergence", event_types)

    def test_cross_pair_return_correlation(self) -> None:
        left = [candle(second, close=str(100 + second)) for second in range(8)]
        right = [candle(second, close=str(200 + 2 * second)) for second in range(8)]

        result = compute_return_correlation(left, right)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreater(result["correlation"], 0.99)
        self.assertEqual(result["sampleSize"], 7)


if __name__ == "__main__":
    unittest.main()
