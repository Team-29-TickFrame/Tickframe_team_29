from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional, Sequence

from ml.pattern_recognition import (
    PATTERN_MODEL_VERSION,
    SUPPORTED_TIMEFRAME,
    WINDOW_SIZE,
)
from ml.pattern_recognition.features import extract_features
from ml.pattern_recognition.model import GaussianNaiveBayesClassifier
from ml.pattern_recognition.weak_labeling import label_window


DEFAULT_CONFIDENCE_THRESHOLD = 0.45


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
        self.model_path = (
            Path(configured_model)
            if configured_model
            else model_path
            or root
            / "ml"
            / "pattern_recognition"
            / "runs"
            / "real-data-v1"
            / "model.json"
        )
        self.confidence_threshold = _confidence_threshold(confidence_threshold)
        self._model: Optional[GaussianNaiveBayesClassifier] = None
        self._load_error: Optional[str] = None

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
        if timeframe != SUPPORTED_TIMEFRAME:
            return {
                "status": "unsupported_timeframe",
                "message": (
                    "ML pattern recognition is currently available only "
                    f"for {SUPPORTED_TIMEFRAME} candles."
                ),
                "modelVersion": PATTERN_MODEL_VERSION,
                "supportedTimeframes": [SUPPORTED_TIMEFRAME],
                "exchange": exchange,
                "instrumentId": instrument_id,
                "timeframe": timeframe,
                "windowSize": WINDOW_SIZE,
                "source": source,
                "generatedAt": generated_at,
                "prediction": None,
                "alternatives": [],
            }

        model = self._load_model()
        if model is None:
            return {
                "status": "model_unavailable",
                "message": self._load_error or "ML model artifact is unavailable.",
                "modelVersion": PATTERN_MODEL_VERSION,
                "supportedTimeframes": [SUPPORTED_TIMEFRAME],
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
                    f"Need {WINDOW_SIZE} complete {SUPPORTED_TIMEFRAME} candles; "
                    f"received {len(closed)}."
                ),
                "modelVersion": PATTERN_MODEL_VERSION,
                "supportedTimeframes": [SUPPORTED_TIMEFRAME],
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
        status = (
            "pattern_detected"
            if prediction.label != "none"
            and prediction.confidence >= self.confidence_threshold
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
            "modelType": "GaussianNaiveBayesClassifier",
            "supportedTimeframes": [SUPPORTED_TIMEFRAME],
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe,
            "windowSize": WINDOW_SIZE,
            "source": source,
            "generatedAt": generated_at,
            "confidenceThreshold": self.confidence_threshold,
            "prediction": {
                "label": prediction.label,
                "confidence": round(prediction.confidence, 6),
            },
            "alternatives": alternatives,
            "dataFrom": int(closed[0]["openTime"]),
            "dataTo": int(closed[-1]["closeTime"]),
            "candleCount": len(closed),
            "ruleBased": rule_based,
            "experimental": True,
        }

    def _load_model(self) -> Optional[GaussianNaiveBayesClassifier]:
        if self._model is not None:
            return self._model
        try:
            self._model = GaussianNaiveBayesClassifier.load(self.model_path)
            self._load_error = None
        except Exception as error:
            self._load_error = str(error)
            self._model = None
        return self._model


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
