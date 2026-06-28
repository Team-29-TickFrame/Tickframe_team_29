from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from . import PATTERN_MODEL_VERSION, SUPPORTED_TIMEFRAME, WINDOW_SIZE
from .dataset import DatasetExample, dataset_summary, generate_dataset
from .features import FEATURE_NAMES, extract_features
from .model import GaussianNaiveBayesClassifier, evaluate_predictions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Train the first maintained synthetic 1m chart-pattern baseline.")
    )
    parser.add_argument(
        "--config",
        default="ml/pattern_recognition/config.json",
        help="Path to the experiment config JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override the configured output directory.",
    )
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=None,
        help="Override synthetic examples per label.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override the configured random seed.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a tiny fast check without changing the main config file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    resolved = resolve_config(config, args)
    validate_config(resolved)

    output_dir = Path(resolved["outputDir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    examples = generate_dataset(
        labels=resolved["labels"],
        samples_per_class=resolved["samplesPerClass"],
        window_size=resolved["windowSize"],
        seed=resolved["seed"],
    )
    train_examples, test_examples = stratified_split(
        examples,
        test_fraction=resolved["testFraction"],
    )

    train_features = [extract_features(example.candles) for example in train_examples]
    train_labels = [example.label for example in train_examples]
    test_features = [extract_features(example.candles) for example in test_examples]
    test_labels = [example.label for example in test_examples]

    model = GaussianNaiveBayesClassifier()
    model.fit(train_features, train_labels, feature_names=FEATURE_NAMES)
    predictions = model.predict(test_features)
    evaluation = evaluate_predictions(
        expected=test_labels,
        predicted=predictions,
        labels=resolved["labels"],
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    dataset_manifest = {
        "dataset": resolved["dataset"],
        "generatedAt": generated_at,
        "timeframe": resolved["timeframe"],
        "windowSize": resolved["windowSize"],
        "seed": resolved["seed"],
        "samplesPerClass": resolved["samplesPerClass"],
        "totalExamples": len(examples),
        "trainExamples": len(train_examples),
        "testExamples": len(test_examples),
        "classCounts": dataset_summary(examples),
        "trainClassCounts": dataset_summary(train_examples),
        "testClassCounts": dataset_summary(test_examples),
        "labels": resolved["labels"],
    }
    metrics = {
        "experiment": resolved["experiment"],
        "modelVersion": PATTERN_MODEL_VERSION,
        "modelType": "GaussianNaiveBayesClassifier",
        "dataset": resolved["dataset"],
        "timeframe": resolved["timeframe"],
        "windowSize": resolved["windowSize"],
        "intendedInferenceCadence": "after_each_closed_1m_candle",
        "supportedTimeframes": [SUPPORTED_TIMEFRAME],
        "confidenceThreshold": resolved["confidenceThreshold"],
        "generatedAt": generated_at,
        "trainExamples": len(train_examples),
        "testExamples": len(test_examples),
        "featureCount": len(FEATURE_NAMES),
        "accuracy": evaluation["accuracy"],
        "macroF1": evaluation["macroF1"],
        "perClass": evaluation["perClass"],
    }
    sample_predictions = [
        {
            "expected": example.label,
            "predicted": model.predict_one(features).label,
            "probabilities": {
                label: round(value, 6)
                for label, value in model.predict_one(features).probabilities.items()
            },
        }
        for example, features in list(zip(test_examples, test_features))[:12]
    ]

    model.save(output_dir / "model.json")
    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "confusion_matrix.json", evaluation["confusionMatrix"])
    write_json(output_dir / "dataset_manifest.json", dataset_manifest)
    write_json(output_dir / "resolved_config.json", resolved)
    write_json(output_dir / "sample_predictions.json", sample_predictions)
    (output_dir / "model-card.md").write_text(
        model_card(metrics=metrics, dataset_manifest=dataset_manifest),
        encoding="utf-8",
    )

    print(
        "trained "
        f"experiment={resolved['experiment']} "
        f"model={PATTERN_MODEL_VERSION} "
        f"accuracy={metrics['accuracy']} "
        f"macro_f1={metrics['macroF1']} "
        f"output_dir={output_dir}"
    )


def resolve_config(
    config: Dict[str, object], args: argparse.Namespace
) -> Dict[str, object]:
    resolved = dict(config)
    if args.output_dir is not None:
        resolved["outputDir"] = args.output_dir
    if args.samples_per_class is not None:
        resolved["samplesPerClass"] = args.samples_per_class
    if args.seed is not None:
        resolved["seed"] = args.seed
    if args.smoke:
        resolved["samplesPerClass"] = min(int(resolved["samplesPerClass"]), 24)
        resolved["outputDir"] = str(Path(str(resolved["outputDir"])) / "smoke")
    return resolved


def validate_config(config: Dict[str, object]) -> None:
    if config["timeframe"] != SUPPORTED_TIMEFRAME:
        raise ValueError(
            f"This pipeline is maintained only for {SUPPORTED_TIMEFRAME} candles."
        )
    if int(config["windowSize"]) != WINDOW_SIZE:
        raise ValueError(f"This pipeline expects {WINDOW_SIZE} candles per example.")
    if not 0.0 < float(config["testFraction"]) < 1.0:
        raise ValueError("testFraction must be between 0 and 1.")
    if int(config["samplesPerClass"]) < 10:
        raise ValueError("samplesPerClass must be at least 10.")


def stratified_split(
    examples: Sequence[DatasetExample],
    *,
    test_fraction: float,
) -> tuple[List[DatasetExample], List[DatasetExample]]:
    by_label: Dict[str, List[DatasetExample]] = {}
    for example in examples:
        by_label.setdefault(example.label, []).append(example)

    train: List[DatasetExample] = []
    test: List[DatasetExample] = []
    for label_examples in by_label.values():
        test_count = max(1, round(len(label_examples) * test_fraction))
        test.extend(label_examples[:test_count])
        train.extend(label_examples[test_count:])
    return train, test


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def model_card(
    *, metrics: Dict[str, object], dataset_manifest: Dict[str, object]
) -> str:
    return f"""# Pattern Baseline v0 Model Card

## Purpose

This artifact is the first maintained Tickframe training pipeline result for
geometric chart-pattern recognition. It is an offline experiment artifact, not
a production trading signal.

## Supported Scope

- Timeframe: `{metrics["timeframe"]}` only
- Window size: `{metrics["windowSize"]}` closed candles
- Intended update cadence: after each newly closed 1m candle
- Supported labels: {", ".join(dataset_manifest["labels"])}
- Confidence threshold planned for product integration: `{metrics["confidenceThreshold"]}`

## Model

- Model version: `{metrics["modelVersion"]}`
- Model type: `{metrics["modelType"]}`
- Feature count: `{metrics["featureCount"]}`

The classifier uses handcrafted OHLCV shape features and a Gaussian Naive Bayes
decision rule. Each label is represented by per-feature means and variances
learned from the synthetic training split.

## Dataset

- Dataset version: `{metrics["dataset"]}`
- Generated at: `{metrics["generatedAt"]}`
- Seed: `{dataset_manifest["seed"]}`
- Total examples: `{dataset_manifest["totalExamples"]}`
- Train examples: `{dataset_manifest["trainExamples"]}`
- Test examples: `{dataset_manifest["testExamples"]}`

## Evaluation

- Accuracy: `{metrics["accuracy"]}`
- Macro F1: `{metrics["macroF1"]}`

See `metrics.json` and `confusion_matrix.json` for the full evaluation output.

## Limitations

- Training data is synthetic and does not prove real-market pattern quality.
- The model is maintained only for 1m candles and 96-candle windows.
- Predictions should be displayed as experimental pattern observations, not as
  buy/sell advice.
- Real-data validation, weak labeling, human labeling, and backtesting are
  planned follow-up work.
"""


if __name__ == "__main__":
    main()
