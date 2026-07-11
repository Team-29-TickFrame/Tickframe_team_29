import json
import math
from pathlib import Path
import tempfile
import unittest

from ml.pattern_recognition.dataset import (
    FeatureExample,
    dataset_summary,
    load_feature_dataset,
)
from ml.pattern_recognition.model import (
    GaussianNaiveBayesClassifier,
    evaluate_predictions,
)


def write_jsonl(path: Path, payloads: list[object]) -> None:
    path.write_text(
        "\n".join(json.dumps(payload) for payload in payloads) + "\n",
        encoding="utf-8",
    )


class FeatureDatasetTests(unittest.TestCase):
    def test_dataset_loads_allowed_labels_and_summarizes_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.jsonl"
            write_jsonl(
                path,
                [
                    {
                        "label": "triangle",
                        "features": [1, "2.5"],
                        "symbol": "BTCUSDT",
                        "openTime": 1_000,
                        "closeTime": 2_000,
                        "source": "fixture",
                    },
                    {
                        "label": "ignored",
                        "features": [],
                    },
                    {
                        "label": "triangle",
                        "features": [3, 4],
                        "symbol": "ETHUSDT",
                        "openTime": 2_000,
                        "closeTime": 3_000,
                    },
                ],
            )

            examples = load_feature_dataset(path, labels=["triangle"])

        self.assertEqual(len(examples), 2)
        self.assertEqual(examples[0].features, [1.0, 2.5])
        self.assertEqual(examples[0].source, "fixture")
        self.assertEqual(examples[1].source, "features.jsonl")
        self.assertEqual(dataset_summary(examples), {"triangle": 2})

    def test_dataset_reports_invalid_json_with_line_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.jsonl"
            path.write_text('{"label": "ignored"}\n{not-json}\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "line 2"):
                load_feature_dataset(path, labels=["triangle"])

    def test_dataset_rejects_non_finite_and_inconsistent_features(self) -> None:
        fixtures = (
            [
                {
                    "label": "triangle",
                    "features": [1, math.inf],
                    "symbol": "BTCUSDT",
                    "openTime": 1,
                    "closeTime": 2,
                }
            ],
            [
                {
                    "label": "triangle",
                    "features": [1, 2],
                    "symbol": "BTCUSDT",
                    "openTime": 1,
                    "closeTime": 2,
                },
                {
                    "label": "triangle",
                    "features": [1],
                    "symbol": "ETHUSDT",
                    "openTime": 2,
                    "closeTime": 3,
                },
            ],
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, payloads in enumerate(fixtures):
                path = Path(directory) / f"features-{index}.jsonl"
                write_jsonl(path, payloads)
                with self.assertRaises(ValueError):
                    load_feature_dataset(path, labels=["triangle"])

    def test_dataset_rejects_missing_or_empty_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.jsonl"
            with self.assertRaises(FileNotFoundError):
                load_feature_dataset(missing, labels=["triangle"])

            empty = Path(directory) / "empty.jsonl"
            write_jsonl(empty, [{"label": "ignored"}])
            with self.assertRaisesRegex(ValueError, "No examples"):
                load_feature_dataset(empty, labels=["triangle"])


class PatternModelValidationTests(unittest.TestCase):
    def test_fit_rejects_wrong_or_non_finite_feature_vectors(self) -> None:
        model = GaussianNaiveBayesClassifier()
        with self.assertRaisesRegex(ValueError, "expected 2"):
            model.fit([[1.0]], ["triangle"], feature_names=["a", "b"])
        with self.assertRaisesRegex(ValueError, "non-finite"):
            model.fit(
                [[1.0, math.nan]],
                ["triangle"],
                feature_names=["a", "b"],
            )

    def test_predict_rejects_unfitted_or_wrong_length_input(self) -> None:
        model = GaussianNaiveBayesClassifier()
        with self.assertRaisesRegex(ValueError, "fitted"):
            model.predict_one([1.0])

        model.fit([[1.0, 2.0]], ["triangle"], feature_names=["a", "b"])
        with self.assertRaisesRegex(ValueError, "Expected 2"):
            model.predict_one([1.0])

    def test_evaluation_rejects_unknown_labels(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown labels"):
            evaluate_predictions(
                expected=["triangle"],
                predicted=["other"],
                labels=["triangle"],
            )

    def test_dataset_summary_is_sorted(self) -> None:
        examples = [
            FeatureExample("z", [1.0], "BTC", 1, 2, "test"),
            FeatureExample("a", [1.0], "ETH", 1, 2, "test"),
            FeatureExample("z", [1.0], "SOL", 1, 2, "test"),
        ]
        self.assertEqual(list(dataset_summary(examples)), ["a", "z"])


if __name__ == "__main__":
    unittest.main()
