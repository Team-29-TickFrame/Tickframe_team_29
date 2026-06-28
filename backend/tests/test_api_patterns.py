import unittest
from unittest.mock import AsyncMock, patch

from backend.app.main import ml_patterns
from ml.pattern_recognition import WINDOW_SIZE
from ml.pattern_recognition.dataset import generate_dataset


def synthetic_candles(label: str, seed: int = 7) -> list[dict]:
    return [
        dict(candle)
        for candle in generate_dataset(
            labels=[label],
            samples_per_class=1,
            window_size=WINDOW_SIZE,
            seed=seed,
        )[0].candles
    ]


class MlPatternApiIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_one_minute_timeframe_does_not_call_history_service(self) -> None:
        with patch(
            "backend.app.main.service.candle_history", new=AsyncMock()
        ) as history:
            result = await ml_patterns(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="5m",
            )

        self.assertEqual(result["status"], "unsupported_timeframe")
        history.assert_not_called()

    async def test_one_minute_endpoint_uses_history_service_and_detector(self) -> None:
        candles = synthetic_candles("double_top")
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

        with patch("backend.app.main.service.candle_history", new=mock_history):
            result = await ml_patterns(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1m",
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


if __name__ == "__main__":
    unittest.main()
