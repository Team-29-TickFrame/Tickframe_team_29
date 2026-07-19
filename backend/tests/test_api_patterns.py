import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.app.main import ml_patterns
from backend.app.pattern_ml import PatternMLDetector
from backend.tests.test_pattern_ml import fixture_candles, write_fixture_model
from ml.pattern_recognition import WINDOW_SIZE


class MlPatternApiIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_multi_timeframe_endpoint_uses_history_service_and_detector(
        self,
    ) -> None:
        for timeframe in ("5m", "15m", "1h", "1d"):
            with self.subTest(timeframe=timeframe):
                candles = fixture_candles("double_top")
                history_response = {
                    "source": "historical_candles",
                    "candles": candles,
                }
                mock_history = AsyncMock(return_value=history_response)

                with tempfile.TemporaryDirectory() as directory:
                    model_path = Path(directory) / "model.json"
                    write_fixture_model(model_path)
                    detector = PatternMLDetector(model_path=model_path)

                    with (
                        patch("backend.app.main.pattern_ml_detector", detector),
                        patch(
                            "backend.app.main.service.candle_history", new=mock_history
                        ),
                    ):
                        result = await ml_patterns(
                            exchange="binance",
                            instrument_id="BTC-USDT",
                            timeframe=timeframe,
                            mode="ml",
                        )

                mock_history.assert_awaited_once_with(
                    exchange="binance",
                    instrument_id="BTC-USDT",
                    timeframe=timeframe,
                    limit=240,
                    from_ms=None,
                    to_ms=None,
                )
                self.assertEqual(result["source"], "historical_candles")
                self.assertEqual(result["timeframe"], timeframe)
                self.assertEqual(result["candleCount"], WINDOW_SIZE)
                self.assertIn(
                    result["status"], {"pattern_detected", "no_reliable_pattern"}
                )

    async def test_one_minute_endpoint_uses_history_service_and_detector(self) -> None:
        candles = fixture_candles("double_top")
        extra_incomplete = [
            {
                **candles[0],
                "openTime": -60_000,
                "closeTime": 0,
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "status": "incomplete",
            }
        ]
        history_response = {
            "source": "historical_candles",
            "candles": [*extra_incomplete, *candles],
        }
        mock_history = AsyncMock(return_value=history_response)

        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.json"
            write_fixture_model(model_path)
            detector = PatternMLDetector(model_path=model_path)

            with (
                patch("backend.app.main.pattern_ml_detector", detector),
                patch("backend.app.main.service.candle_history", new=mock_history),
            ):
                result = await ml_patterns(
                    exchange="binance",
                    instrument_id="BTC-USDT",
                    timeframe="1m",
                    mode="ml",
                )

        mock_history.assert_awaited_once_with(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1m",
            limit=240,
            from_ms=None,
            to_ms=None,
        )
        self.assertEqual(result["source"], "historical_candles")
        self.assertEqual(result["candleCount"], WINDOW_SIZE)
        self.assertIn(result["status"], {"pattern_detected", "no_reliable_pattern"})
        self.assertIsNotNone(result["prediction"])
        self.assertIn("ruleBased", result)

    async def test_rule_based_mode_uses_history_without_model_inference(self) -> None:
        candles = fixture_candles("double_top")
        history_response = {
            "source": "historical_candles",
            "candles": candles,
        }
        mock_history = AsyncMock(return_value=history_response)
        detector = PatternMLDetector(model_path=Path("missing-model.json"))

        with (
            patch.object(
                detector,
                "_load_model",
                side_effect=AssertionError("rule-based API must not load ML model"),
            ),
            patch("backend.app.main.pattern_ml_detector", detector),
            patch("backend.app.main.service.candle_history", new=mock_history),
        ):
            result = await ml_patterns(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1m",
                mode="rule_based",
            )

        mock_history.assert_awaited_once_with(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1m",
            limit=240,
            from_ms=None,
            to_ms=None,
        )
        self.assertEqual(result["detectorMode"], "rule_based")
        self.assertEqual(result["modelType"], "RuleBasedDetector")
        self.assertEqual(result["status"], "pattern_detected")
        self.assertEqual(result["prediction"]["label"], "double_top")
        self.assertEqual(result["ruleBased"]["label"], "double_top")


if __name__ == "__main__":
    unittest.main()
