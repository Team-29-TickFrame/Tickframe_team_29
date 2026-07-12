from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from . import PATTERN_MODEL_VERSION, WINDOW_SIZE
from .dataset import FeatureExample, dataset_summary, load_feature_dataset
from .features import FEATURE_NAMES
from .model import BoostedTreeClassifier, create_classifier, evaluate_predictions


DATASET_PATHS_BY_TIMEFRAME = {
    "1m": "features.jsonl",
    "5m": "features-5m.jsonl",
    "15m": "features-15m.jsonl",
    "1h": "features-1h.jsonl",
    "1d": "features-1d.jsonl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the maintained real-data chart-pattern baseline."
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
        "--dataset-path",
        default=None,
        help="Override the prepared feature dataset JSONL path.",
    )
    parser.add_argument(
        "--timeframe",
        choices=sorted(DATASET_PATHS_BY_TIMEFRAME.keys()),
        default=None,
        help=(
            "Prepared dataset timeframe to train on. When --dataset-path is not "
            "provided, this selects the matching features*.jsonl file."
        ),
    )
    parser.add_argument(
        "--max-examples-per-class",
        type=int,
        default=None,
        help="Override the maximum loaded examples per label.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Kept in the resolved config for experiment reproducibility.",
    )
    parser.add_argument(
        "--model-type",
        choices=[
            "auto",
            "lightgbm",
            "hist_gradient_boosting",
            "gaussian_nb",
        ],
        default=None,
        help=(
            "Classifier to train. auto tries LightGBM first, then "
            "scikit-learn HistGradientBoosting."
        ),
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

    output_dir = Path(str(resolved["outputDir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    examples = load_balanced_dataset(
        Path(str(resolved["datasetPath"])),
        labels=list(resolved["labels"]),
        max_examples_per_class=int(resolved["maxExamplesPerClass"]),
    )
    train_examples, test_examples = chronological_stratified_split(
        examples,
        test_fraction=float(resolved["testFraction"]),
    )

    train_features = [example.features for example in train_examples]
    train_labels = [example.label for example in train_examples]
    test_features = [example.features for example in test_examples]
    test_labels = [example.label for example in test_examples]

    model = create_classifier(
        str(resolved.get("modelType", "auto")),
        seed=int(resolved["seed"]),
    )
    model.fit(train_features, train_labels, feature_names=FEATURE_NAMES)
    model_type = model.__class__.__name__
    model_backend = (
        model.resolved_backend
        if isinstance(model, BoostedTreeClassifier)
        else "baseline"
    )
    predictions = model.predict(test_features)
    evaluation = evaluate_predictions(
        expected=test_labels,
        predicted=predictions,
        labels=list(resolved["labels"]),
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    dataset_manifest = {
        "dataset": resolved["dataset"],
        "datasetPath": resolved["datasetPath"],
        "generatedAt": generated_at,
        "timeframe": resolved["timeframe"],
        "windowSize": resolved["windowSize"],
        "seed": resolved["seed"],
        "maxExamplesPerClass": resolved["maxExamplesPerClass"],
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
        "modelType": model_type,
        "modelBackend": model_backend,
        "baselineModelType": "GaussianNaiveBayesClassifier",
        "dataset": resolved["dataset"],
        "timeframe": resolved["timeframe"],
        "windowSize": resolved["windowSize"],
        "intendedInferenceCadence": f"after_each_closed_{resolved['timeframe']}_candle",
        "supportedTimeframes": [resolved["timeframe"]],
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
            "symbol": example.symbol,
            "openTime": example.open_time,
            "closeTime": example.close_time,
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
        f"type={metrics['modelType']} "
        f"backend={metrics['modelBackend']} "
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
    if args.timeframe is not None:
        resolved["timeframe"] = args.timeframe
        if args.dataset_path is None:
            resolved["datasetPath"] = str(
                dataset_path_for_timeframe(
                    Path(str(resolved["datasetPath"])),
                    args.timeframe,
                )
            )
    if args.dataset_path is not None:
        resolved["datasetPath"] = args.dataset_path
    if args.max_examples_per_class is not None:
        resolved["maxExamplesPerClass"] = args.max_examples_per_class
    if args.seed is not None:
        resolved["seed"] = args.seed
    if args.model_type is not None:
        resolved["modelType"] = args.model_type
    if args.smoke:
        resolved["maxExamplesPerClass"] = min(int(resolved["maxExamplesPerClass"]), 24)
        resolved["outputDir"] = str(Path(str(resolved["outputDir"])) / "smoke")
    return resolved


def validate_config(config: Dict[str, object]) -> None:
    allowed_timeframes = list(
        config.get("datasetTimeframes", DATASET_PATHS_BY_TIMEFRAME.keys())
    )
    if config["timeframe"] not in allowed_timeframes:
        raise ValueError(
            "This pipeline has prepared dataset support only for "
            f"{', '.join(allowed_timeframes)} candles."
        )
    if int(config["windowSize"]) != WINDOW_SIZE:
        raise ValueError(f"This pipeline expects {WINDOW_SIZE} candles per example.")
    if not 0.0 < float(config["testFraction"]) < 1.0:
        raise ValueError("testFraction must be between 0 and 1.")
    if not str(config.get("datasetPath", "")).strip():
        raise ValueError("datasetPath must point to a prepared feature JSONL file.")
    if int(config["maxExamplesPerClass"]) < 10:
        raise ValueError("maxExamplesPerClass must be at least 10.")
    if str(config.get("modelType", "")).strip() == "":
        config["modelType"] = "auto"


def dataset_path_for_timeframe(current_path: Path, timeframe: str) -> Path:
    filename = DATASET_PATHS_BY_TIMEFRAME[timeframe]
    return current_path.parent / filename


def load_balanced_dataset(
    path: Path,
    *,
    labels: Sequence[str],
    max_examples_per_class: int,
) -> List[FeatureExample]:
    loaded = load_feature_dataset(path, labels=labels)
    by_label: Dict[str, List[FeatureExample]] = {}
    for example in loaded:
        by_label.setdefault(example.label, []).append(example)

    examples: List[FeatureExample] = []
    for label in labels:
        ordered = sorted(by_label.get(label, []), key=lambda item: item.open_time)
        examples.extend(evenly_sample(ordered, max_examples_per_class))
    if not examples:
        raise ValueError(f"No examples were loaded from {path}.")
    return examples


def chronological_stratified_split(
    examples: Sequence[FeatureExample],
    *,
    test_fraction: float,
) -> tuple[List[FeatureExample], List[FeatureExample]]:
    by_label: Dict[str, List[FeatureExample]] = {}
    for example in examples:
        by_label.setdefault(example.label, []).append(example)

    train: List[FeatureExample] = []
    test: List[FeatureExample] = []
    for label_examples in by_label.values():
        ordered = sorted(label_examples, key=lambda item: item.open_time)
        test_count = max(1, round(len(ordered) * test_fraction))
        train.extend(ordered[:-test_count])
        test.extend(ordered[-test_count:])
    return train, test


def evenly_sample(
    examples: Sequence[FeatureExample], limit: int
) -> List[FeatureExample]:
    if len(examples) <= limit:
        return list(examples)
    if limit <= 1:
        return [examples[-1]]

    last_index = len(examples) - 1
    selected: List[FeatureExample] = []
    seen_indices = set()
    for index in range(limit):
        source_index = round(index * last_index / (limit - 1))
        if source_index in seen_indices:
            continue
        selected.append(examples[source_index])
        seen_indices.add(source_index)
    return selected


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def model_card(
    *, metrics: Dict[str, object], dataset_manifest: Dict[str, object]
) -> str:
    return f"""# Pattern Real Data v1 Model Card

## Purpose

This artifact is the maintained Tickframe training pipeline result for
geometric chart-pattern recognition on real Binance public market data. It is
an offline experiment artifact, not a production trading signal.

## Supported Scope

- Timeframe: `{metrics["timeframe"]}`
- Window size: `{metrics["windowSize"]}` closed candles
- Intended update cadence: after each newly closed {metrics["timeframe"]} candle
- Supported labels: {", ".join(dataset_manifest["labels"])}
- Confidence threshold planned for product integration: `{metrics["confidenceThreshold"]}`

## Model

- Model version: `{metrics["modelVersion"]}`
- Model type: `{metrics["modelType"]}`
- Model backend: `{metrics.get("modelBackend", "baseline")}`
- Feature count: `{metrics["featureCount"]}`

The classifier uses handcrafted OHLCV shape features learned from weak-labeled
real Binance public market data. `auto` training attempts LightGBM first and
falls back to scikit-learn HistGradientBoosting when LightGBM is unavailable.
Gaussian Naive Bayes remains available as the baseline model.

## Dataset

- Dataset version: `{metrics["dataset"]}`
- Dataset path: `{dataset_manifest["datasetPath"]}`
- Generated at: `{metrics["generatedAt"]}`
- Total examples: `{dataset_manifest["totalExamples"]}`
- Train examples: `{dataset_manifest["trainExamples"]}`
- Test examples: `{dataset_manifest["testExamples"]}`

## Evaluation

- Accuracy: `{metrics["accuracy"]}`
- Macro F1: `{metrics["macroF1"]}`

See `metrics.json` and `confusion_matrix.json` for the full evaluation output.

## Limitations

- Training labels are weak labels generated from rule-based chart definitions.
- This artifact is trained only for its listed timeframe and 96-candle windows.
- Predictions should be displayed as experimental pattern observations, not as
  buy/sell advice.
- Human review, cross-exchange validation, and backtesting remain required
  before treating the model as product-quality.
"""


if __name__ == "__main__":
    main()
