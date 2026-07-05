from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


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
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            label = str(payload["label"])
            if label not in allowed:
                continue
            examples.append(
                FeatureExample(
                    label=label,
                    features=[float(value) for value in payload["features"]],
                    symbol=str(payload["symbol"]),
                    open_time=int(payload["openTime"]),
                    close_time=int(payload["closeTime"]),
                    source=str(payload.get("source", path.name)),
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
