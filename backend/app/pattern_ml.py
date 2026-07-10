from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional, Sequence

from ml.pattern_recognition import (
    PATTERN_MODEL_VERSION,
    WINDOW_SIZE,
)
from ml.pattern_recognition.features import extract_features
from ml.pattern_recognition.model import PatternClassifier, load_pattern_model
from ml.pattern_recognition.weak_labeling import label_window


DEFAULT_CONFIDENCE_THRESHOLD = 0.45
DEFAULT_MODEL_RUN = "lightgbm-clean-1m-v1"
DEFAULT_MODEL_RUNS = {
    "1m": "lightgbm-clean-1m-v1",
    "5m": "lightgbm-clean-5m-v1",
    "15m": "lightgbm-clean-15m-v1",
    "1h": "lightgbm-clean-1h-v1",
    "1d": "lightgbm-clean-1d-v1",
}
SUPPORTED_PATTERN_TIMEFRAMES = tuple(DEFAULT_MODEL_RUNS.keys())
CLASS_BASE_THRESHOLDS = {
    "double_bottom": 0.56,
    "double_top": 0.58,
    "flag": 0.62,
    "head_and_shoulders": 0.60,
    "triangle": 0.64,
    "none": 1.0,
}


def unix_ms() -> int:
    return int(time.time() * 1000)


class PatternMLDetector:
    def __init__(
        self,
        *,
        model_path: Optional[Path] = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        configured_model = os.getenv("TICKFRAME_PATTERN_MODEL_PATH")
        fallback_model_path = (
            Path(configured_model) if configured_model else model_path
        )
        self.model_paths = {
            timeframe: fallback_model_path
            or root
            / "ml"
            / "pattern_recognition"
            / "runs"
            / run_name
            / "model.json"
            for timeframe, run_name in DEFAULT_MODEL_RUNS.items()
        }
        self.model_path = self.model_paths["1m"]
        self.confidence_threshold = _confidence_threshold(confidence_threshold)
        self._models: Dict[str, PatternClassifier] = {}
        self._load_errors: Dict[str, str] = {}

    def predict(
        self,
        *,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        source: str,
        candles: Sequence[Dict[str, object]],
    ) -> Dict[str, object]:
        generated_at = unix_ms()
        if timeframe not in SUPPORTED_PATTERN_TIMEFRAMES:
            return {
                "status": "unsupported_timeframe",
                "message": (
                    "ML pattern recognition is currently available only for "
                    f"{', '.join(SUPPORTED_PATTERN_TIMEFRAMES)} candles."
                ),
                "modelVersion": PATTERN_MODEL_VERSION,
                "supportedTimeframes": list(SUPPORTED_PATTERN_TIMEFRAMES),
                "exchange": exchange,
                "instrumentId": instrument_id,
                "timeframe": timeframe,
                "windowSize": WINDOW_SIZE,
                "source": source,
                "generatedAt": generated_at,
                "prediction": None,
                "alternatives": [],
            }

        model = self._load_model(timeframe)
        if model is None:
            return {
                "status": "model_unavailable",
                "message": self._load_errors.get(timeframe)
                or "ML model artifact is unavailable.",
                "modelVersion": PATTERN_MODEL_VERSION,
                "supportedTimeframes": list(SUPPORTED_PATTERN_TIMEFRAMES),
                "exchange": exchange,
                "instrumentId": instrument_id,
                "timeframe": timeframe,
                "windowSize": WINDOW_SIZE,
                "source": source,
                "generatedAt": generated_at,
                "prediction": None,
                "alternatives": [],
            }

        closed = [
            candle
            for candle in candles
            if _has_complete_ohlcv(candle) and str(candle.get("status")) != "incomplete"
        ][-WINDOW_SIZE:]
        if len(closed) < WINDOW_SIZE:
            return {
                "status": "insufficient_data",
                "message": (
                    f"Need {WINDOW_SIZE} complete {timeframe} candles; "
                    f"received {len(closed)}."
                ),
                "modelVersion": PATTERN_MODEL_VERSION,
                "supportedTimeframes": list(SUPPORTED_PATTERN_TIMEFRAMES),
                "exchange": exchange,
                "instrumentId": instrument_id,
                "timeframe": timeframe,
                "windowSize": WINDOW_SIZE,
                "source": source,
                "generatedAt": generated_at,
                "prediction": None,
                "alternatives": [],
                "dataFrom": None,
                "dataTo": None,
                "candleCount": len(closed),
            }

        features = extract_features(closed)
        rule_based = _rule_based_explanation(closed)
        prediction = model.predict_one(features)
        alternatives = [
            {
                "label": label,
                "confidence": round(confidence, 6),
            }
            for label, confidence in sorted(
                prediction.probabilities.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        threshold = _dynamic_threshold(
            label=prediction.label,
            confidence=prediction.confidence,
            probabilities=prediction.probabilities,
            rule_based=rule_based,
            configured_floor=self.confidence_threshold,
        )
        passes_threshold = (
            prediction.label != "none"
            and prediction.confidence >= threshold["recommendedThreshold"]
        )
        status = (
            "pattern_detected"
            if passes_threshold
            else "no_reliable_pattern"
        )
        return {
            "status": status,
            "message": (
                "Real-data baseline matched a chart pattern."
                if status == "pattern_detected"
                else "No reliable ML pattern is above the configured threshold."
            ),
            "modelVersion": PATTERN_MODEL_VERSION,
            "modelType": self._model_type(model),
            "supportedTimeframes": list(SUPPORTED_PATTERN_TIMEFRAMES),
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "windowSize": WINDOW_SIZE,
            "source": source,
            "generatedAt": generated_at,
            "confidenceThreshold": threshold["recommendedThreshold"],
            "configuredConfidenceThreshold": self.confidence_threshold,
            "recommendedThreshold": threshold["recommendedThreshold"],
            "passesThreshold": passes_threshold,
            "thresholdMode": "dynamic",
            "prediction": {
                "label": prediction.label,
                "confidence": round(prediction.confidence, 6),
                "recommendedThreshold": threshold["recommendedThreshold"],
                "passesThreshold": passes_threshold,
                "thresholdMode": "dynamic",
                "thresholdReason": threshold["reason"],
            },
            "alternatives": alternatives,
            "dataFrom": int(closed[0]["openTime"]),
            "dataTo": int(closed[-1]["closeTime"]),
            "candleCount": len(closed),
            "ruleBased": rule_based,
            "experimental": True,
        }

    def _load_model(self, timeframe: str = "1m") -> Optional[PatternClassifier]:
        if timeframe in self._models:
            return self._models[timeframe]
        try:
            self._models[timeframe] = load_pattern_model(self.model_paths[timeframe])
            self._load_errors.pop(timeframe, None)
        except Exception as error:
            self._load_errors[timeframe] = str(error)
            self._models.pop(timeframe, None)
        return self._models.get(timeframe)

    def _model_type(self, model: PatternClassifier) -> str:
        backend = getattr(model, "resolved_backend", None)
        if backend:
            return f"{model.__class__.__name__}:{backend}"
        return model.__class__.__name__


def _has_complete_ohlcv(candle: Dict[str, object]) -> bool:
    return all(
        candle.get(field) is not None for field in ("open", "high", "low", "close")
    )


def _rule_based_explanation(
    candles: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    weak_label = label_window(candles)
    anchors = []
    for name, index in weak_label.anchors.items():
        if index < 0 or index >= len(candles):
            continue
        candle = candles[index]
        anchors.append(
            {
                "name": name,
                "index": index,
                "openTime": int(candle["openTime"]),
                "closeTime": int(candle["closeTime"]),
                "open": _float_or_none(candle.get("open")),
                "high": _float_or_none(candle.get("high")),
                "low": _float_or_none(candle.get("low")),
                "close": _float_or_none(candle.get("close")),
            }
        )
    return {
        "label": weak_label.label,
        "score": round(weak_label.score, 6),
        "reason": weak_label.reason,
        "anchors": anchors,
    }


def _float_or_none(value: object) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _dynamic_threshold(
    *,
    label: str,
    confidence: float,
    probabilities: Dict[str, float],
    rule_based: Dict[str, object],
    configured_floor: float,
) -> Dict[str, object]:
    base = CLASS_BASE_THRESHOLDS.get(label, 0.62)
    ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    second_confidence = ordered[1][1] if len(ordered) > 1 else 0.0
    margin = confidence - second_confidence
    reason_parts = [f"base={base:.2f}", f"margin={margin:.3f}"]

    threshold = base
    if margin < 0.08:
        threshold += 0.08
        reason_parts.append("low_margin=+0.08")
    elif margin < 0.15:
        threshold += 0.04
        reason_parts.append("medium_margin=+0.04")

    rule_label = str(rule_based.get("label", "none"))
    rule_score = float(rule_based.get("score", 0.0) or 0.0)
    if label != "none" and rule_label == label:
        adjustment = 0.08 if rule_score >= 0.70 else 0.05
        threshold -= adjustment
        reason_parts.append(f"rule_agreement=-{adjustment:.2f}")
    elif rule_label != "none" and rule_label != label:
        threshold += 0.04
        reason_parts.append("rule_disagreement=+0.04")

    if confidence >= 0.85 and margin >= 0.20:
        threshold -= 0.03
        reason_parts.append("clear_model_signal=-0.03")

    threshold = min(0.92, max(configured_floor, threshold))
    return {
        "recommendedThreshold": round(threshold, 6),
        "reason": "; ".join(reason_parts),
    }


def _confidence_threshold(default: float) -> float:
    raw_value = os.getenv("TICKFRAME_PATTERN_CONFIDENCE_THRESHOLD")
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        return default
    return min(0.99, max(0.05, value))


pattern_ml_detector = PatternMLDetector()
