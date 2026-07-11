import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.pattern_ml import PatternMLDetector, SUPPORTED_PATTERN_TIMEFRAMES
from ml.pattern_recognition import PATTERN_MODEL_VERSION, WINDOW_SIZE
from ml.pattern_recognition.features import FEATURE_NAMES, extract_features
from ml.pattern_recognition.model import GaussianNaiveBayesClassifier


def fixture_candles(label: str = "double_top") -> list[dict]:
    if label == "double_top":
        points = [
            (0.00, 100.0),
            (0.24, 108.0),
            (0.50, 101.0),
            (0.74, 107.8),
            (1.00, 99.0),
        ]
    else:
        points = [(0.00, 100.0), (1.00, 101.5)]

    closes = _interpolate(points, WINDOW_SIZE)
    candles: list[dict] = []
    previous = closes[0]
    for index, close in enumerate(closes):
        open_price = previous
        high = max(open_price, close) + 0.15
        low = min(open_price, close) - 0.15
        candles.append(
            {
                "openTime": index * 60_000,
                "closeTime": (index + 1) * 60_000,
                "open": round(open_price, 8),
                "high": round(high, 8),
                "low": round(low, 8),
                "close": round(close, 8),
                "baseVolume": 100.0 + index,
                "quoteVolume": (100.0 + index) * close,
                "tradeCount": 10 + index,
                "timeframe": "1m",
                "status": "complete",
            }
        )
        previous = close
    return candles


def write_fixture_model(path: Path) -> None:
    examples = [
        (extract_features(fixture_candles("double_top")), "double_top"),
        (extract_features(fixture_candles("none")), "none"),
    ]
    model = GaussianNaiveBayesClassifier()
    model.fit(
        [features for features, _ in examples],
        [label for _, label in examples],
        feature_names=FEATURE_NAMES,
    )
    model.save(path)


class PatternMLDetectorTests(unittest.TestCase):
    def test_unsupported_timeframe_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.json"
            write_fixture_model(model_path)
            detector = PatternMLDetector(model_path=model_path)

            result = detector.predict(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1s",
                source="test",
                candles=[],
            )

        self.assertEqual(result["status"], "unsupported_timeframe")
        self.assertIn("1m", result["supportedTimeframes"])
        self.assertIn("5m", result["supportedTimeframes"])
        self.assertIsNone(result["prediction"])

    def test_five_minute_timeframe_uses_configured_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.json"
            write_fixture_model(model_path)
            detector = PatternMLDetector(model_path=model_path)
            candles = fixture_candles("double_top")

            result = detector.predict(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="5m",
                source="fixture-test",
                candles=candles,
            )

        self.assertIn(result["status"], {"pattern_detected", "no_reliable_pattern"})
        self.assertEqual(result["timeframe"], "5m")
        self.assertEqual(result["candleCount"], WINDOW_SIZE)
        self.assertIsNotNone(result["prediction"])

    def test_insufficient_complete_candles_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.json"
            write_fixture_model(model_path)
            detector = PatternMLDetector(model_path=model_path)
            candles = fixture_candles("double_top")[:20]
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

    def test_detector_loads_model_and_detects_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.json"
            write_fixture_model(model_path)
            detector = PatternMLDetector(model_path=model_path)

            result = detector.predict(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1m",
                source="fixture-test",
                candles=fixture_candles("double_top"),
            )

        self.assertEqual(result["status"], "pattern_detected")
        self.assertEqual(result["prediction"]["label"], "double_top")
        self.assertIn("recommendedThreshold", result["prediction"])
        self.assertIn("passesThreshold", result["prediction"])
        self.assertTrue(result["prediction"]["passesThreshold"])
        self.assertEqual(result["thresholdMode"], "dynamic")
        self.assertEqual(result["candleCount"], WINDOW_SIZE)
        self.assertEqual(result["dataFrom"], 0)
        self.assertEqual(result["dataTo"], WINDOW_SIZE * 60_000)
        self.assertEqual(result["ruleBased"]["label"], "double_top")
        self.assertGreater(len(result["ruleBased"]["anchors"]), 0)

    def test_model_unavailable_is_non_crashing_status(self) -> None:
        detector = PatternMLDetector(model_path=Path("missing-model.json"))

        result = detector.predict(
            exchange="binance",
            instrument_id="BTC-USDT",
            timeframe="1m",
            source="test",
            candles=fixture_candles("none"),
        )

        self.assertEqual(result["status"], "model_unavailable")
        self.assertIsNone(result["prediction"])

    def test_confidence_threshold_env_override_is_clamped(self) -> None:
        with patch.dict(
            "os.environ",
            {"TICKFRAME_PATTERN_CONFIDENCE_THRESHOLD": "2.0"},
        ):
            detector = PatternMLDetector(model_path=Path("missing-model.json"))

        self.assertEqual(detector.confidence_threshold, 0.99)

        with patch.dict(
            "os.environ",
            {"TICKFRAME_PATTERN_CONFIDENCE_THRESHOLD": "invalid"},
        ):
            fallback = PatternMLDetector(
                model_path=Path("missing-model.json"),
                confidence_threshold=0.42,
            )

        self.assertEqual(fallback.confidence_threshold, 0.42)


class PatternMLArtifactTests(unittest.TestCase):
    def test_default_real_data_model_artifact_loads(self) -> None:
        detector = PatternMLDetector()

        self.assertIn("lightgbm-clean-1m-v1", str(detector.model_path))
        self.assertIsNotNone(detector._load_model())
        self.assertNotIn("1m", detector._load_errors)

    def test_default_real_data_model_artifacts_load_for_all_timeframes(self) -> None:
        detector = PatternMLDetector()

        for timeframe in SUPPORTED_PATTERN_TIMEFRAMES:
            with self.subTest(timeframe=timeframe):
                self.assertIsNotNone(detector._load_model(timeframe))
                self.assertNotIn(timeframe, detector._load_errors)

    def test_detector_accepts_absolute_model_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_model = Path(directory) / "model.json"
            write_fixture_model(temporary_model)
            detector = PatternMLDetector(model_path=temporary_model)

            result = detector.predict(
                exchange="binance",
                instrument_id="BTC-USDT",
                timeframe="1m",
                source="fixture-test",
                candles=fixture_candles("none"),
            )

        self.assertIn(result["status"], {"pattern_detected", "no_reliable_pattern"})
        self.assertIsNotNone(result["prediction"])
        self.assertIn("recommendedThreshold", result["prediction"])
        self.assertIn("passesThreshold", result["prediction"])
        self.assertEqual(result["modelVersion"], PATTERN_MODEL_VERSION)


def _interpolate(points: list[tuple[float, float]], length: int) -> list[float]:
    indexed = [
        (min(length - 1, max(0, round(position * (length - 1)))), value)
        for position, value in points
    ]
    output = [indexed[0][1]] * length
    for (left_index, left_value), (right_index, right_value) in zip(
        indexed, indexed[1:]
    ):
        span = max(1, right_index - left_index)
        for index in range(left_index, right_index + 1):
            progress = (index - left_index) / span
            output[index] = left_value + (right_value - left_value) * progress
    return output


if __name__ == "__main__":
    unittest.main()
