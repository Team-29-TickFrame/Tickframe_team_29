import unittest
from decimal import Decimal

from backend.app.models import Trade
from backend.app.observability import LatencyObservability


def trade() -> Trade:
    return Trade(
        exchange="binance",
        market_type="spot",
        instrument_id="BTC-USDT",
        exchange_symbol="BTCUSDT",
        trade_id="1",
        exchange_timestamp_ms=1_000,
        received_timestamp_ms=1_025,
        price=Decimal("64000.5"),
        base_quantity=Decimal("0.01"),
        side="buy",
    )


class ObservabilityTests(unittest.TestCase):
    def test_trade_latency_is_exported_to_snapshot_and_prometheus(self) -> None:
        telemetry = LatencyObservability()

        telemetry.observe_trade(trade(), processed_at_ms=1_040)

        snapshot = telemetry.snapshot(now_ms=2_000)
        market = snapshot["markets"][0]
        self.assertEqual(market["exchange"], "binance")
        self.assertEqual(market["instrumentId"], "BTC-USDT")
        self.assertEqual(market["price"], 64000.5)
        self.assertEqual(market["tradeLatencyMs"], 25)

        stages = {
            item["stage"]: item
            for item in snapshot["latency"]
            if item["exchange"] == "binance"
        }
        self.assertEqual(stages["exchange_to_backend"]["p95Ms"], 25)
        self.assertEqual(stages["backend_queue"]["p95Ms"], 15)

        prometheus = telemetry.prometheus_text(now_ms=2_000)
        self.assertIn("tickframe_latency_ms_bucket", prometheus)
        self.assertIn('stage="exchange_to_backend"', prometheus)
        self.assertIn("tickframe_latest_price", prometheus)

    def test_frontend_display_samples_measure_end_to_end_latency(self) -> None:
        telemetry = LatencyObservability()

        accepted = telemetry.observe_frontend_display(
            [
                {
                    "channel": "markets",
                    "exchange": "bybit",
                    "instrumentId": "ETH-USDT",
                    "price": "2500.25",
                    "exchangeTimestamp": 10_000,
                    "backendReceivedAt": 10_030,
                    "backendGeneratedAt": 10_050,
                    "frontendReceivedAt": 10_090,
                    "displayedAt": 10_120,
                }
            ],
            accepted_at_ms=10_140,
        )

        self.assertEqual(accepted, 1)
        snapshot = telemetry.snapshot(now_ms=10_200)
        stages = {
            item["stage"]: item
            for item in snapshot["latency"]
            if item["exchange"] == "bybit"
        }
        self.assertEqual(stages["backend_to_frontend"]["p95Ms"], 40)
        self.assertEqual(stages["frontend_render"]["p95Ms"], 30)
        self.assertEqual(stages["backend_to_display"]["p95Ms"], 90)
        self.assertEqual(stages["exchange_to_display"]["p95Ms"], 120)
        self.assertEqual(stages["data_to_display"]["p95Ms"], 120)


if __name__ == "__main__":
    unittest.main()
