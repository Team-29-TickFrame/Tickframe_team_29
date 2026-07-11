from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Dict, List, Optional, Sequence


@dataclass(frozen=True)
class WeakLabel:
    label: str
    score: float
    anchors: Dict[str, int]
    reason: str


def label_window(candles: Sequence[Dict[str, object]]) -> WeakLabel:
    if len(candles) < 32:
        return _none("window_too_short")

    highs = [_number(candle["high"]) for candle in candles]
    lows = [_number(candle["low"]) for candle in candles]
    closes = [_number(candle["close"]) for candle in candles]
    volumes = [_number(candle.get("baseVolume", 0.0)) for candle in candles]

    candidates = [
        _double_top(highs, lows, closes),
        _double_bottom(highs, lows, closes),
        _head_and_shoulders(highs, lows, closes),
        _triangle(highs, lows, closes),
        _flag(closes, volumes),
    ]
    detected = [candidate for candidate in candidates if candidate.label != "none"]
    if not detected:
        return _none("no_rule_matched")
    return max(detected, key=lambda candidate: candidate.score)


def _double_top(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> WeakLabel:
    pivot_highs = _pivot_indices(highs, pivot_type="high")
    best: Optional[WeakLabel] = None
    for left, right in _pivot_pairs(pivot_highs, min_span=10, max_span=72):
        left_value = highs[left]
        right_value = highs[right]
        average_top = (left_value + right_value) / 2
        if average_top <= 0:
            continue

        similarity = abs(left_value - right_value) / average_top * 100
        if similarity > 1.25:
            continue

        neckline_index = _min_index(lows, left + 1, right)
        neckline = lows[neckline_index]
        depth = (average_top - neckline) / average_top * 100
        if depth < 1.0:
            continue

        breakout = _first_below(closes, neckline, start=right + 1)
        if breakout is None:
            continue

        score = 0.54
        score += min(0.18, (1.25 - similarity) / 1.25 * 0.18)
        score += min(0.18, depth / 4.0 * 0.18)
        score += min(0.08, (len(closes) - breakout) / len(closes) * 0.08)
        label = WeakLabel(
            label="double_top",
            score=round(min(score, 0.98), 6),
            anchors={
                "left_top": left,
                "neckline": neckline_index,
                "right_top": right,
                "breakout": breakout,
            },
            reason=(
                f"top_similarity={similarity:.3f}; "
                f"middle_retrace={depth:.3f}; neckline_break=true"
            ),
        )
        best = _better(best, label)
    return best or _none("double_top_not_matched")


def _double_bottom(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> WeakLabel:
    pivot_lows = _pivot_indices(lows, pivot_type="low")
    best: Optional[WeakLabel] = None
    for left, right in _pivot_pairs(pivot_lows, min_span=10, max_span=72):
        left_value = lows[left]
        right_value = lows[right]
        average_bottom = (left_value + right_value) / 2
        if average_bottom <= 0:
            continue

        similarity = abs(left_value - right_value) / average_bottom * 100
        if similarity > 1.25:
            continue

        neckline_index = _max_index(highs, left + 1, right)
        neckline = highs[neckline_index]
        depth = (neckline - average_bottom) / average_bottom * 100
        if depth < 1.0:
            continue

        breakout = _first_above(closes, neckline, start=right + 1)
        if breakout is None:
            continue

        score = 0.54
        score += min(0.18, (1.25 - similarity) / 1.25 * 0.18)
        score += min(0.18, depth / 4.0 * 0.18)
        score += min(0.08, (len(closes) - breakout) / len(closes) * 0.08)
        label = WeakLabel(
            label="double_bottom",
            score=round(min(score, 0.98), 6),
            anchors={
                "left_bottom": left,
                "neckline": neckline_index,
                "right_bottom": right,
                "breakout": breakout,
            },
            reason=(
                f"bottom_similarity={similarity:.3f}; "
                f"middle_retrace={depth:.3f}; neckline_break=true"
            ),
        )
        best = _better(best, label)
    return best or _none("double_bottom_not_matched")


def _head_and_shoulders(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> WeakLabel:
    pivot_highs = _pivot_indices(highs, pivot_type="high")
    best: Optional[WeakLabel] = None
    for left, head, right in zip(pivot_highs, pivot_highs[1:], pivot_highs[2:]):
        if head - left < 8 or right - head < 8 or right - left > 84:
            continue

        left_value = highs[left]
        head_value = highs[head]
        right_value = highs[right]
        shoulders = (left_value + right_value) / 2
        if shoulders <= 0:
            continue

        head_height = (head_value - shoulders) / shoulders * 100
        shoulder_similarity = abs(left_value - right_value) / shoulders * 100
        if head_height < 1.2 or shoulder_similarity > 1.8:
            continue

        left_neck = _min_index(lows, left + 1, head)
        right_neck = _min_index(lows, head + 1, right)
        neckline = (lows[left_neck] + lows[right_neck]) / 2
        breakout = _first_below(closes, neckline, start=right + 1)
        if breakout is None:
            continue

        score = 0.52
        score += min(0.2, head_height / 4.0 * 0.2)
        score += min(0.16, (1.8 - shoulder_similarity) / 1.8 * 0.16)
        score += 0.08
        label = WeakLabel(
            label="head_and_shoulders",
            score=round(min(score, 0.98), 6),
            anchors={
                "left_shoulder": left,
                "head": head,
                "right_shoulder": right,
                "left_neckline": left_neck,
                "right_neckline": right_neck,
                "breakout": breakout,
            },
            reason=(
                f"head_height={head_height:.3f}; "
                f"shoulder_similarity={shoulder_similarity:.3f}; "
                "neckline_break=true"
            ),
        )
        best = _better(best, label)
    return best or _none("head_and_shoulders_not_matched")


def _triangle(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> WeakLabel:
    pivot_highs = _pivot_indices(highs, pivot_type="high")
    pivot_lows = _pivot_indices(lows, pivot_type="low")
    if len(pivot_highs) < 2 or len(pivot_lows) < 2:
        return _none("triangle_needs_pivots")

    upper_slope = _slope([highs[index] for index in pivot_highs[-4:]])
    lower_slope = _slope([lows[index] for index in pivot_lows[-4:]])
    early_range = mean(high - low for high, low in zip(highs[:16], lows[:16]))
    late_range = mean(high - low for high, low in zip(highs[-16:], lows[-16:]))
    compression = _pct_change(early_range, late_range) if early_range > 0 else 0.0

    converging = upper_slope < 0 and lower_slope > 0
    flat_top = abs(upper_slope) < 0.05 and lower_slope > 0
    flat_bottom = upper_slope < 0 and abs(lower_slope) < 0.05
    if not (converging or flat_top or flat_bottom):
        return _none("triangle_lines_not_converging")
    if compression > -20.0:
        return _none("triangle_range_not_compressing")

    close_span = max(closes) - min(closes)
    if close_span <= 0:
        return _none("triangle_flat_close")

    score = 0.5
    score += min(0.24, abs(compression) / 70.0 * 0.24)
    score += min(0.14, (len(pivot_highs) + len(pivot_lows)) / 10.0 * 0.14)
    score += 0.08 if converging else 0.04
    return WeakLabel(
        label="triangle",
        score=round(min(score, 0.95), 6),
        anchors={
            "first_pivot_high": pivot_highs[0],
            "last_pivot_high": pivot_highs[-1],
            "first_pivot_low": pivot_lows[0],
            "last_pivot_low": pivot_lows[-1],
        },
        reason=(
            f"upper_slope={upper_slope:.6f}; lower_slope={lower_slope:.6f}; "
            f"range_compression={compression:.3f}"
        ),
    )


def _flag(closes: Sequence[float], volumes: Sequence[float]) -> WeakLabel:
    if len(closes) < 48:
        return _none("flag_window_too_short")

    impulse_end = max(12, len(closes) // 4)
    impulse_return = _pct_change(closes[0], closes[impulse_end])
    if abs(impulse_return) < 2.0:
        return _none("flag_impulse_too_small")

    post_return = _pct_change(closes[impulse_end], closes[-1])
    retrace_ratio = abs(post_return) / abs(impulse_return)
    same_direction = impulse_return * post_return > 0
    if retrace_ratio > 0.55 or same_direction:
        return _none("flag_consolidation_not_valid")

    post_closes = closes[impulse_end:]
    returns = [
        _pct_change(left, right)
        for left, right in zip(post_closes, post_closes[1:])
        if left > 0
    ]
    if not returns:
        return _none("flag_no_post_returns")

    post_volatility = pstdev(returns) if len(returns) > 1 else 0.0
    first_volume = mean(volumes[:impulse_end]) if volumes else 0.0
    post_volume = mean(volumes[impulse_end:]) if volumes else 0.0
    volume_cooldown = post_volume < first_volume * 1.25 if first_volume > 0 else True
    if post_volatility > abs(impulse_return) / 3:
        return _none("flag_consolidation_too_volatile")

    score = 0.52
    score += min(0.2, abs(impulse_return) / 8.0 * 0.2)
    score += min(0.14, (0.55 - retrace_ratio) / 0.55 * 0.14)
    score += 0.06 if volume_cooldown else 0.0
    return WeakLabel(
        label="flag",
        score=round(min(score, 0.95), 6),
        anchors={
            "impulse_start": 0,
            "impulse_end": impulse_end,
            "flag_end": len(closes) - 1,
        },
        reason=(
            f"impulse_return={impulse_return:.3f}; "
            f"post_impulse_return={post_return:.3f}; "
            f"retrace_ratio={retrace_ratio:.3f}"
        ),
    )


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


def _pivot_pairs(
    pivots: Sequence[int], *, min_span: int, max_span: int
) -> List[tuple[int, int]]:
    pairs: List[tuple[int, int]] = []
    for left_index, left in enumerate(pivots):
        for right in pivots[left_index + 1 :]:
            span = right - left
            if min_span <= span <= max_span:
                pairs.append((left, right))
    return pairs


def _number(value: object) -> float:
    return float(value)


def _pct_change(start: float, end: float) -> float:
    return (end - start) / start * 100.0 if start else 0.0


def _slope(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    start = values[0]
    return _pct_change(start, values[-1]) / max(1, len(values) - 1)


def _min_index(values: Sequence[float], start: int, stop: int) -> int:
    return min(range(start, stop), key=lambda index: values[index])


def _max_index(values: Sequence[float], start: int, stop: int) -> int:
    return max(range(start, stop), key=lambda index: values[index])


def _first_below(values: Sequence[float], level: float, *, start: int) -> Optional[int]:
    for index in range(start, len(values)):
        if values[index] < level:
            return index
    return None


def _first_above(values: Sequence[float], level: float, *, start: int) -> Optional[int]:
    for index in range(start, len(values)):
        if values[index] > level:
            return index
    return None


def _better(left: Optional[WeakLabel], right: WeakLabel) -> WeakLabel:
    return right if left is None or right.score > left.score else left


def _none(reason: str) -> WeakLabel:
    return WeakLabel(label="none", score=0.0, anchors={}, reason=reason)
