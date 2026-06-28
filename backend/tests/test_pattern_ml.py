import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.pattern_ml import PatternMLDetector
from ml.pattern_recognition import WINDOW_SIZE
from ml.pattern_recognition.dataset import generate_dataset


MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "ml"
    / "pattern_recognition"
    / "runs"
    / "baseline-v0"
    / "model.json"
)


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


class PatternMLDetectorTests(unittest.TestCase):
    def test_unsupported_timeframe_is_explicit(self) -> None:
        detector = PatternMLDetector(model_path=MODEL_PATH)

        result = detector.predict(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="5m",
            source="test",
            candles=[],
        )

        self.assertEqual(result["status"], "unsupported_timeframe")
        self.assertEqual(result["supportedTimeframes"], ["1m"])
        self.assertIsNone(result["prediction"])

    def test_insufficient_complete_candles_are_reported(self) -> None:
        detector = PatternMLDetector(model_path=MODEL_PATH)
        candles = synthetic_candles("double_top")[:20]
        candles[0]["close"] = None

        result = detector.predict(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1m",
            source="test",
            candles=candles,
        )

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["candleCount"], 19)

    def test_detector_loads_model_and_detects_synthetic_pattern(self) -> None:
        detector = PatternMLDetector(model_path=MODEL_PATH)

        result = detector.predict(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1m",
            source="synthetic-test",
            candles=synthetic_candles("double_top"),
        )

        self.assertEqual(result["status"], "pattern_detected")
        self.assertEqual(result["prediction"]["label"], "double_top")
        self.assertEqual(result["candleCount"], WINDOW_SIZE)
        self.assertEqual(result["dataFrom"], 0)
        self.assertEqual(result["dataTo"], WINDOW_SIZE * 60_000)

    def test_model_unavailable_is_non_crashing_status(self) -> None:
        detector = PatternMLDetector(model_path=Path("missing-model.json"))

        result = detector.predict(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1m",
            source="test",
            candles=synthetic_candles("triangle"),
        )

        self.assertEqual(result["status"], "model_unavailable")
        self.assertIsNone(result["prediction"])

    def test_confidence_threshold_env_override_is_clamped(self) -> None:
        with patch.dict(
            "os.environ",
            {"TICKFRAME_PATTERN_CONFIDENCE_THRESHOLD": "2.0"},
        ):
            detector = PatternMLDetector(model_path=MODEL_PATH)

        self.assertEqual(detector.confidence_threshold, 0.99)

        with patch.dict(
            "os.environ",
            {"TICKFRAME_PATTERN_CONFIDENCE_THRESHOLD": "invalid"},
        ):
            fallback = PatternMLDetector(
                model_path=MODEL_PATH,
                confidence_threshold=0.42,
            )

        self.assertEqual(fallback.confidence_threshold, 0.42)


class PatternMLArtifactTests(unittest.TestCase):
    def test_saved_model_artifact_is_committed_and_small(self) -> None:
        self.assertTrue(MODEL_PATH.exists())
        self.assertLess(MODEL_PATH.stat().st_size, 200_000)

    def test_detector_accepts_absolute_model_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_model = Path(directory) / "model.json"
            temporary_model.write_text(MODEL_PATH.read_text(encoding="utf-8"))
            detector = PatternMLDetector(model_path=temporary_model)

            result = detector.predict(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1m",
                source="synthetic-test",
                candles=synthetic_candles("triangle", seed=11),
            )

        self.assertIn(result["status"], {"pattern_detected", "no_reliable_pattern"})
        self.assertIsNotNone(result["prediction"])


if __name__ == "__main__":
    unittest.main()
