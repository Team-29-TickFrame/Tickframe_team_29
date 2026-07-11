from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


LABELS = [
    "head_and_shoulders",
    "triangle",
    "flag",
    "double_top",
    "double_bottom",
    "none",
]


@dataclass(frozen=True)
class FeatureExample:
    label: str
    features: List[float]
    symbol: str
    open_time: int
    close_time: int
    source: str


def load_feature_dataset(path: Path, *, labels: Sequence[str]) -> List[FeatureExample]:
    if not path.exists():
        raise FileNotFoundError(f"Prepared feature dataset does not exist: {path}")

    allowed = set(labels)
    examples: List[FeatureExample] = []
    feature_count: Optional[int] = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON in {path} at line {line_number}: {error.msg}"
                ) from error
            if not isinstance(payload, dict):
                raise ValueError(
                    f"Expected a JSON object in {path} at line {line_number}."
                )

            if "label" not in payload:
                raise ValueError(f"Expected a label in {path} at line {line_number}.")
            label = str(payload["label"])
            if label not in allowed:
                continue

            raw_features = payload.get("features")
            if not isinstance(raw_features, list) or not raw_features:
                raise ValueError(
                    f"Expected a non-empty features array in {path} at line "
                    f"{line_number}."
                )
            try:
                features = [float(value) for value in raw_features]
                open_time = int(payload["openTime"])
                close_time = int(payload["closeTime"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid feature example in {path} at line {line_number}."
                ) from error
            if not all(math.isfinite(value) for value in features):
                raise ValueError(
                    f"Features must be finite in {path} at line {line_number}."
                )
            if close_time <= open_time:
                raise ValueError(
                    f"closeTime must be greater than openTime in {path} at line "
                    f"{line_number}."
                )
            if feature_count is None:
                feature_count = len(features)
            elif len(features) != feature_count:
                raise ValueError(
                    f"Inconsistent feature count in {path} at line {line_number}: "
                    f"expected {feature_count}, got {len(features)}."
                )

            symbol = str(payload.get("symbol", "")).strip()
            if not symbol:
                raise ValueError(
                    f"Expected a non-empty symbol in {path} at line {line_number}."
                )
            examples.append(
                FeatureExample(
                    label=label,
                    features=features,
                    symbol=symbol,
                    open_time=open_time,
                    close_time=close_time,
                    source=str(payload.get("source") or path.name),
                )
            )

    if not examples:
        raise ValueError(
            f"No examples for labels {sorted(allowed)} were loaded from {path}."
        )
    return examples


def dataset_summary(examples: Iterable[FeatureExample]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for example in examples:
        counts[example.label] = counts.get(example.label, 0) + 1
    return dict(sorted(counts.items()))
