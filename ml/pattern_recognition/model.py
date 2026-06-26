from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


VARIANCE_FLOOR = 1e-9


@dataclass
class Prediction:
    label: str
    confidence: float
    probabilities: Dict[str, float]


class GaussianNaiveBayesClassifier:
    """Small dependency-free baseline classifier for maintained experiments."""

    def __init__(self) -> None:
        self.labels: List[str] = []
        self.class_priors: Dict[str, float] = {}
        self.means: Dict[str, List[float]] = {}
        self.variances: Dict[str, List[float]] = {}
        self.feature_names: List[str] = []

    def fit(
        self,
        features: Sequence[Sequence[float]],
        labels: Sequence[str],
        *,
        feature_names: Sequence[str],
    ) -> None:
        if len(features) != len(labels):
            raise ValueError("features and labels must have the same length.")
        if not features:
            raise ValueError("Cannot train on an empty dataset.")

        self.feature_names = list(feature_names)
        self.labels = sorted(set(labels))
        total = len(labels)

        for label in self.labels:
            class_rows = [
                list(row)
                for row, row_label in zip(features, labels)
                if row_label == label
            ]
            if not class_rows:
                continue
            self.class_priors[label] = len(class_rows) / total
            self.means[label] = _column_means(class_rows)
            self.variances[label] = _column_variances(class_rows, self.means[label])

    def predict(self, features: Sequence[Sequence[float]]) -> List[str]:
        return [self.predict_one(row).label for row in features]

    def predict_one(self, features: Sequence[float]) -> Prediction:
        probabilities = self.predict_proba_one(features)
        label = max(probabilities, key=probabilities.get)
        return Prediction(
            label=label,
            confidence=probabilities[label],
            probabilities=probabilities,
        )

    def predict_proba_one(self, features: Sequence[float]) -> Dict[str, float]:
        log_scores = {
            label: self._log_score(label, features)
            for label in self.labels
        }
        return _softmax(log_scores)

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "GaussianNaiveBayesClassifier":
        payload = json.loads(path.read_text(encoding="utf-8"))
        model = cls()
        model.labels = list(payload["labels"])
        model.class_priors = {
            str(label): float(value)
            for label, value in payload["classPriors"].items()
        }
        model.means = {
            str(label): [float(item) for item in values]
            for label, values in payload["means"].items()
        }
        model.variances = {
            str(label): [float(item) for item in values]
            for label, values in payload["variances"].items()
        }
        model.feature_names = list(payload["featureNames"])
        return model

    def to_dict(self) -> Dict[str, object]:
        return {
            "modelType": "GaussianNaiveBayesClassifier",
            "labels": self.labels,
            "featureNames": self.feature_names,
            "classPriors": self.class_priors,
            "means": self.means,
            "variances": self.variances,
        }

    def _log_score(self, label: str, features: Sequence[float]) -> float:
        prior = max(self.class_priors[label], VARIANCE_FLOOR)
        score = math.log(prior)
        for value, mean, variance in zip(
            features,
            self.means[label],
            self.variances[label],
        ):
            variance = max(variance, VARIANCE_FLOOR)
            score += -0.5 * math.log(2.0 * math.pi * variance)
            score += -((value - mean) ** 2) / (2.0 * variance)
        return score


def evaluate_predictions(
    *,
    expected: Sequence[str],
    predicted: Sequence[str],
    labels: Sequence[str],
) -> Dict[str, object]:
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have the same length.")

    confusion = {
        label: {other: 0 for other in labels}
        for label in labels
    }
    for actual, guess in zip(expected, predicted):
        confusion[actual][guess] += 1

    correct = sum(1 for actual, guess in zip(expected, predicted) if actual == guess)
    per_class: Dict[str, Dict[str, float]] = {}
    f1_values: List[float] = []

    for label in labels:
        true_positive = confusion[label][label]
        false_positive = sum(confusion[other][label] for other in labels if other != label)
        false_negative = sum(confusion[label][other] for other in labels if other != label)
        precision = _safe_ratio(true_positive, true_positive + false_positive)
        recall = _safe_ratio(true_positive, true_positive + false_negative)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        per_class[label] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }
        f1_values.append(f1)

    return {
        "accuracy": round(_safe_ratio(correct, len(expected)), 6),
        "macroF1": round(sum(f1_values) / len(f1_values), 6),
        "perClass": per_class,
        "confusionMatrix": confusion,
    }


def _column_means(rows: Sequence[Sequence[float]]) -> List[float]:
    columns = len(rows[0])
    return [
        sum(row[index] for row in rows) / len(rows)
        for index in range(columns)
    ]


def _column_variances(
    rows: Sequence[Sequence[float]],
    means: Sequence[float],
) -> List[float]:
    return [
        max(
            VARIANCE_FLOOR,
            sum((row[index] - means[index]) ** 2 for row in rows) / len(rows),
        )
        for index in range(len(means))
    ]


def _softmax(log_scores: Dict[str, float]) -> Dict[str, float]:
    max_score = max(log_scores.values())
    exp_scores = {
        label: math.exp(score - max_score)
        for label, score in log_scores.items()
    }
    total = sum(exp_scores.values())
    return {
        label: value / total
        for label, value in exp_scores.items()
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
