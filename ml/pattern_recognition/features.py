from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Sequence


FEATURE_NAMES = [
    "total_return_pct",
    "volatility_pct",
    "mean_abs_return_pct",
    "max_drawdown_pct",
    "max_runup_pct",
    "pivot_high_count",
    "pivot_low_count",
    "top_similarity_pct",
    "bottom_similarity_pct",
    "middle_retrace_pct",
    "head_height_pct",
    "shoulder_similarity_pct",
    "upper_slope_pct",
    "lower_slope_pct",
    "range_compression_pct",
    "impulse_return_pct",
    "post_impulse_return_pct",
    "average_body_to_range",
    "average_upper_wick_pct",
    "average_lower_wick_pct",
    "volume_trend_pct",
    "volume_volatility_pct",
]

RESAMPLED_CLOSE_POINTS = 16
FEATURE_NAMES.extend(
    f"close_shape_{index:02d}" for index in range(RESAMPLED_CLOSE_POINTS)
)


def extract_features(candles: Sequence[Dict[str, object]]) -> List[float]:
    if len(candles) < 8:
        raise ValueError("At least 8 candles are required for pattern features.")

    opens = [_number(candle["open"]) for candle in candles]
    highs = [_number(candle["high"]) for candle in candles]
    lows = [_number(candle["low"]) for candle in candles]
    closes = [_number(candle["close"]) for candle in candles]
    volumes = [_number(candle.get("baseVolume", 0.0)) for candle in candles]

    if any(value <= 0 for value in closes):
        raise ValueError("All close values must be positive.")

    returns = _pct_returns(closes)
    pivot_highs = _pivot_indices(highs, pivot_type="high")
    pivot_lows = _pivot_indices(lows, pivot_type="low")
    top_similarity, middle_retrace = _double_extreme_features(
        pivot_highs,
        highs,
        lows,
        mode="top",
    )
    bottom_similarity, _ = _double_extreme_features(
        pivot_lows,
        lows,
        highs,
        mode="bottom",
    )
    head_height, shoulder_similarity = _head_and_shoulders_features(highs)
    upper_slope, lower_slope, compression = _triangle_features(highs, lows)
    impulse_return, post_impulse_return = _flag_features(closes)
    body_to_range, upper_wick, lower_wick = _wick_features(opens, highs, lows, closes)
    volume_trend, volume_volatility = _volume_features(volumes)
    shape = _resampled_shape(closes, RESAMPLED_CLOSE_POINTS)

    features = [
        _pct_change(closes[0], closes[-1]),
        pstdev(returns) if len(returns) > 1 else 0.0,
        mean(abs(value) for value in returns) if returns else 0.0,
        _max_drawdown(closes),
        _max_runup(closes),
        float(len(pivot_highs)),
        float(len(pivot_lows)),
        top_similarity,
        bottom_similarity,
        middle_retrace,
        head_height,
        shoulder_similarity,
        upper_slope,
        lower_slope,
        compression,
        impulse_return,
        post_impulse_return,
        body_to_range,
        upper_wick,
        lower_wick,
        volume_trend,
        volume_volatility,
        *shape,
    ]
    return [_finite(value) for value in features]


def feature_matrix(
    examples: Iterable[Sequence[Dict[str, object]]],
) -> List[List[float]]:
    return [extract_features(candles) for candles in examples]


def _number(value: object) -> float:
    if value is None:
        raise ValueError("Feature extraction does not accept null candle values.")
    return float(value)


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end - start) / start * 100.0


def _pct_returns(values: Sequence[float]) -> List[float]:
    return [
        _pct_change(left, right) for left, right in zip(values, values[1:]) if left > 0
    ]


def _pivot_indices(
    values: Sequence[float], *, pivot_type: str, radius: int = 2
) -> List[int]:
    pivots: List[int] = []
    for index in range(radius, len(values) - radius):
        left = values[index - radius : index]
        right = values[index + 1 : index + radius + 1]
        center = values[index]
        if pivot_type == "high":
            if all(center > value for value in left) and all(
                center >= value for value in right
            ):
                pivots.append(index)
        else:
            if all(center < value for value in left) and all(
                center <= value for value in right
            ):
                pivots.append(index)
    return pivots


def _double_extreme_features(
    pivots: Sequence[int],
    edge_values: Sequence[float],
    middle_values: Sequence[float],
    *,
    mode: str,
) -> tuple[float, float]:
    if len(pivots) < 2:
        return 100.0, 0.0
    best_similarity = 100.0
    best_retrace = 0.0
    for left, right in zip(pivots, pivots[1:]):
        if right - left < 8:
            continue
        left_value = edge_values[left]
        right_value = edge_values[right]
        average = (left_value + right_value) / 2.0
        if average <= 0:
            continue
        similarity = abs(left_value - right_value) / average * 100.0
        between = middle_values[left + 1 : right]
        if not between:
            continue
        if mode == "top":
            retrace = (average - min(between)) / average * 100.0
        else:
            retrace = (max(between) - average) / average * 100.0
        if similarity < best_similarity:
            best_similarity = similarity
            best_retrace = retrace
    return best_similarity, best_retrace


def _head_and_shoulders_features(highs: Sequence[float]) -> tuple[float, float]:
    third = len(highs) // 3
    left = max(highs[:third])
    head = max(highs[third : third * 2])
    right = max(highs[third * 2 :])
    shoulders = (left + right) / 2.0
    if shoulders <= 0:
        return 0.0, 100.0
    head_height = (head - shoulders) / shoulders * 100.0
    shoulder_similarity = abs(left - right) / shoulders * 100.0
    return head_height, shoulder_similarity


def _triangle_features(
    highs: Sequence[float], lows: Sequence[float]
) -> tuple[float, float, float]:
    span = max(1, len(highs) - 1)
    upper_slope = _pct_change(highs[0], highs[-1]) / span * 100.0
    lower_slope = _pct_change(lows[0], lows[-1]) / span * 100.0
    early_range = mean(high - low for high, low in zip(highs[:16], lows[:16]))
    late_range = mean(high - low for high, low in zip(highs[-16:], lows[-16:]))
    compression = _pct_change(early_range, late_range) if early_range > 0 else 0.0
    return upper_slope, lower_slope, compression


def _flag_features(closes: Sequence[float]) -> tuple[float, float]:
    impulse_end = max(2, len(closes) // 4)
    impulse_return = _pct_change(closes[0], closes[impulse_end])
    post_impulse_return = _pct_change(closes[impulse_end], closes[-1])
    return impulse_return, post_impulse_return


def _wick_features(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> tuple[float, float, float]:
    body_ratios: List[float] = []
    upper_wicks: List[float] = []
    lower_wicks: List[float] = []
    for open_, high, low, close in zip(opens, highs, lows, closes):
        candle_range = max(0.000001, high - low)
        body_high = max(open_, close)
        body_low = min(open_, close)
        body_ratios.append(abs(close - open_) / candle_range)
        upper_wicks.append((high - body_high) / candle_range * 100.0)
        lower_wicks.append((body_low - low) / candle_range * 100.0)
    return mean(body_ratios), mean(upper_wicks), mean(lower_wicks)


def _volume_features(volumes: Sequence[float]) -> tuple[float, float]:
    if not volumes:
        return 0.0, 0.0
    midpoint = len(volumes) // 2
    first = mean(volumes[:midpoint])
    second = mean(volumes[midpoint:])
    trend = _pct_change(first, second) if first > 0 else 0.0
    volatility = pstdev(volumes) / mean(volumes) * 100.0 if mean(volumes) > 0 else 0.0
    return trend, volatility


def _max_drawdown(values: Sequence[float]) -> float:
    peak = values[0]
    drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, _pct_change(peak, value))
    return drawdown


def _max_runup(values: Sequence[float]) -> float:
    trough = values[0]
    runup = 0.0
    for value in values:
        trough = min(trough, value)
        runup = max(runup, _pct_change(trough, value))
    return runup


def _resampled_shape(values: Sequence[float], points: int) -> List[float]:
    base = values[0]
    if points <= 1:
        return [0.0]
    output: List[float] = []
    for index in range(points):
        source = round(index * (len(values) - 1) / (points - 1))
        output.append(_pct_change(base, values[source]))
    return output


def _finite(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return value
