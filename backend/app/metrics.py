from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional


METRICS_VERSION = "metrics-v3"
RSI_PERIOD = 14
SHORT_MOMENTUM_PERIOD = 5
MOMENTUM_PERIOD = 14
REALIZED_VOLATILITY_WINDOW = 20
RANGE_VOLATILITY_WINDOW = 20
MEAN_REVERSION_WINDOW = 20
VOLUME_SPIKE_WINDOW = 20
VOLUME_SPIKE_THRESHOLD = 3.0
VWAP_EXTENSION_THRESHOLD_PCT = 1.0
PIVOT_RADIUS = 2
MIN_PATTERN_SPAN = 4
MAX_PATTERN_SPAN = 60
DOUBLE_PATTERN_TOLERANCE_PCT = 0.6
DOUBLE_PATTERN_DEPTH_PCT = 0.8
DIVERGENCE_PRICE_MOVE_PCT = 0.35
DIVERGENCE_RSI_DELTA = 5.0
DIVERGENCE_VOLUME_DROP_PCT = 20.0
MEAN_REVERSION_Z_THRESHOLD = 2.0


def compute_metrics(
    candles: Iterable[Dict[str, Any]],
    *,
    timeframe: str,
) -> Dict[str, Any]:
    ordered = sorted(candles, key=lambda candle: int(candle["openTime"]))
    opens = [_decimal_or_none(candle.get("open")) for candle in ordered]
    closes = [_decimal_or_none(candle.get("close")) for candle in ordered]
    highs = [_decimal_or_none(candle.get("high")) for candle in ordered]
    lows = [_decimal_or_none(candle.get("low")) for candle in ordered]
    volumes = [
        _decimal_or_zero(candle.get("baseVolume"))
        for candle in ordered
    ]

    cumulative_base = Decimal("0")
    cumulative_quote = Decimal("0")
    log_returns: List[Optional[float]] = []
    points: List[Dict[str, Any]] = []

    for index, candle in enumerate(ordered):
        close = closes[index]
        volume = volumes[index]
        quote_volume = _decimal_or_zero(candle.get("quoteVolume"))

        if close is not None and volume > 0:
            cumulative_base += volume
            cumulative_quote += quote_volume

        previous_close = closes[index - 1] if index > 0 else None
        log_return = _log_return(previous_close, close)
        log_returns.append(log_return)

        vwap = (
            cumulative_quote / cumulative_base
            if cumulative_base > 0
            else None
        )
        realized_volatility = _realized_volatility(
            log_returns,
            index,
            REALIZED_VOLATILITY_WINDOW,
        )
        rsi = _rsi(closes, index, RSI_PERIOD)
        short_momentum = _momentum(closes, index, SHORT_MOMENTUM_PERIOD)
        momentum = _momentum(closes, index, MOMENTUM_PERIOD)
        parkinson_volatility = _parkinson_volatility(
            highs,
            lows,
            index,
            RANGE_VOLATILITY_WINDOW,
        )
        garman_klass_volatility = _garman_klass_volatility(
            opens,
            highs,
            lows,
            closes,
            index,
            RANGE_VOLATILITY_WINDOW,
        )
        mean_reversion = _mean_reversion(
            closes,
            index,
            MEAN_REVERSION_WINDOW,
        )
        price_volume_divergence = _price_volume_divergence(
            closes,
            volumes,
            index,
            MOMENTUM_PERIOD,
        )
        volume_spike = _volume_spike_ratio(
            volumes,
            index,
            VOLUME_SPIKE_WINDOW,
        )
        vwap_deviation = _vwap_deviation(close, vwap)

        points.append(
            {
                "openTime": int(candle["openTime"]),
                "closeTime": int(candle["closeTime"]),
                "close": _float_or_none(close),
                "vwap": _float_or_none(vwap),
                "vwapDeviationPct": _round_or_none(vwap_deviation),
                "realizedVolatilityPct": _round_or_none(realized_volatility),
                "parkinsonVolatilityPct": _round_or_none(parkinson_volatility),
                "garmanKlassVolatilityPct": _round_or_none(
                    garman_klass_volatility
                ),
                "rsi": _round_or_none(rsi),
                "shortMomentumPct": _round_or_none(short_momentum),
                "momentumPct": _round_or_none(momentum),
                "meanReversionZScore": _round_or_none(
                    mean_reversion["z_score"] if mean_reversion else None
                ),
                "distanceToMeanPct": _round_or_none(
                    mean_reversion["distance_pct"] if mean_reversion else None
                ),
                "priceVolumeDivergencePct": _round_or_none(
                    price_volume_divergence
                ),
                "volumeSpikeRatio": _round_or_none(volume_spike),
                "baseVolume": _float_or_none(volume),
                "tradeCount": int(candle.get("tradeCount", 0)),
                "status": candle.get("status"),
            }
        )

    return {
        "version": METRICS_VERSION,
        "timeframe": timeframe,
        "windows": {
            "rsi": RSI_PERIOD,
            "shortMomentum": SHORT_MOMENTUM_PERIOD,
            "momentum": MOMENTUM_PERIOD,
            "realizedVolatility": REALIZED_VOLATILITY_WINDOW,
            "rangeVolatility": RANGE_VOLATILITY_WINDOW,
            "meanReversion": MEAN_REVERSION_WINDOW,
            "priceVolumeDivergence": MOMENTUM_PERIOD,
            "volumeSpike": VOLUME_SPIKE_WINDOW,
        },
        "count": len(points),
        "latest": _latest_complete_point(points),
        "summary": _window_summary(
            highs=highs,
            lows=lows,
            volumes=volumes,
            candles=ordered,
        ),
        "events": collect_events(
            points,
            highs=highs,
            lows=lows,
        ),
        "points": points,
    }


def collect_events(
    points: List[Dict[str, Any]],
    *,
    highs: List[Optional[Decimal]],
    lows: List[Optional[Decimal]],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    events = metric_events(points)
    events.extend(pattern_events(points, highs=highs, lows=lows))
    return sorted(events, key=lambda event: event["openTime"], reverse=True)[:limit]


def metric_events(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    volatility_history: List[float] = []

    for point in points:
        volatility = point["realizedVolatilityPct"]
        if volatility is not None:
            previous = volatility_history[-20:]
            baseline = sum(previous) / len(previous) if previous else None
            if baseline and volatility >= baseline * 2 and volatility >= 0.05:
                events.append(
                    _event(
                        point,
                        kind="volatility_shift",
                        metric="realizedVolatilityPct",
                        severity="high" if volatility >= baseline * 3 else "medium",
                        value=volatility,
                        threshold=baseline * 2,
                        confidence=min(0.99, 0.55 + min(volatility / baseline, 4) / 10),
                        description=(
                            "Realized volatility expanded versus its recent baseline."
                        ),
                    )
                )
            volatility_history.append(volatility)

        volume_spike = point["volumeSpikeRatio"]
        if volume_spike is not None and volume_spike >= VOLUME_SPIKE_THRESHOLD:
            events.append(
                _event(
                    point,
                    kind="volume_spike",
                    metric="volumeSpikeRatio",
                    severity="high" if volume_spike >= 5 else "medium",
                    value=volume_spike,
                    threshold=VOLUME_SPIKE_THRESHOLD,
                    confidence=min(0.99, 0.5 + min(volume_spike / 10, 0.45)),
                    description="Current base volume is above its rolling baseline.",
                )
            )

        vwap_deviation = point["vwapDeviationPct"]
        if (
            vwap_deviation is not None
            and abs(vwap_deviation) >= VWAP_EXTENSION_THRESHOLD_PCT
        ):
            direction = "above" if vwap_deviation > 0 else "below"
            events.append(
                _event(
                    point,
                    kind="vwap_extension",
                    metric="vwapDeviationPct",
                    severity="high" if abs(vwap_deviation) >= 2 else "medium",
                    value=vwap_deviation,
                    threshold=VWAP_EXTENSION_THRESHOLD_PCT,
                    confidence=min(0.99, 0.52 + min(abs(vwap_deviation) / 10, 0.43)),
                    description=f"Close is extended {direction} session VWAP.",
                )
            )

        rsi = point["rsi"]
        if rsi is not None and (rsi >= 70 or rsi <= 30):
            direction = "upper" if rsi >= 70 else "lower"
            events.append(
                _event(
                    point,
                    kind="rsi_extreme",
                    metric="rsi",
                    severity="medium",
                    value=rsi,
                    threshold=70 if rsi >= 70 else 30,
                    confidence=min(0.95, 0.5 + abs(rsi - 50) / 100),
                    description=f"RSI reached the {direction} observation band.",
                )
            )

        mean_reversion = point["meanReversionZScore"]
        if (
            mean_reversion is not None
            and abs(mean_reversion) >= MEAN_REVERSION_Z_THRESHOLD
        ):
            direction = "above" if mean_reversion > 0 else "below"
            events.append(
                _event(
                    point,
                    kind="mean_reversion_stretch",
                    metric="meanReversionZScore",
                    severity=(
                        "high"
                        if abs(mean_reversion) >= MEAN_REVERSION_Z_THRESHOLD * 1.5
                        else "medium"
                    ),
                    value=mean_reversion,
                    threshold=MEAN_REVERSION_Z_THRESHOLD,
                    confidence=min(0.98, 0.52 + abs(mean_reversion) / 8),
                    description=(
                        f"Close is stretched {direction} its rolling mean."
                    ),
                )
            )

        price_volume_divergence = point["priceVolumeDivergencePct"]
        if (
            price_volume_divergence is not None
            and abs(price_volume_divergence) >= DIVERGENCE_VOLUME_DROP_PCT
        ):
            events.append(
                _event(
                    point,
                    kind="price_volume_divergence",
                    metric="priceVolumeDivergencePct",
                    severity=(
                        "high"
                        if abs(price_volume_divergence)
                        >= DIVERGENCE_VOLUME_DROP_PCT * 1.5
                        else "medium"
                    ),
                    value=price_volume_divergence,
                    threshold=DIVERGENCE_VOLUME_DROP_PCT,
                    confidence=min(
                        0.96,
                        0.52 + abs(price_volume_divergence) / 120,
                    ),
                    description=(
                        "Price moved while base volume contracted versus "
                        "its lookback window."
                    ),
                )
            )

    return events


def pattern_events(
    points: List[Dict[str, Any]],
    *,
    highs: List[Optional[Decimal]],
    lows: List[Optional[Decimal]],
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    high_values = [_float_or_none(value) for value in highs]
    low_values = [_float_or_none(value) for value in lows]
    rsi_values = [point["rsi"] for point in points]
    volume_values = [point["baseVolume"] for point in points]

    pivot_highs = _pivot_indices(high_values, pivot_type="high")
    pivot_lows = _pivot_indices(low_values, pivot_type="low")

    double_top = _latest_double_pattern(
        points,
        pivots=pivot_highs,
        edge_values=high_values,
        middle_values=low_values,
        kind="double_top",
        direction="highs",
        middle_mode="min",
    )
    if double_top is not None:
        events.append(double_top)

    double_bottom = _latest_double_pattern(
        points,
        pivots=pivot_lows,
        edge_values=low_values,
        middle_values=high_values,
        kind="double_bottom",
        direction="lows",
        middle_mode="max",
    )
    if double_bottom is not None:
        events.append(double_bottom)

    bearish_divergence = _latest_rsi_divergence(
        points,
        pivots=pivot_highs,
        price_values=high_values,
        rsi_values=rsi_values,
        kind="bearish_rsi_divergence",
        direction="high",
    )
    if bearish_divergence is not None:
        events.append(bearish_divergence)

    bullish_divergence = _latest_rsi_divergence(
        points,
        pivots=pivot_lows,
        price_values=low_values,
        rsi_values=rsi_values,
        kind="bullish_rsi_divergence",
        direction="low",
    )
    if bullish_divergence is not None:
        events.append(bullish_divergence)

    bearish_volume_divergence = _latest_price_volume_divergence(
        points,
        pivots=pivot_highs,
        price_values=high_values,
        volume_values=volume_values,
        kind="bearish_price_volume_divergence",
        direction="high",
    )
    if bearish_volume_divergence is not None:
        events.append(bearish_volume_divergence)

    bullish_volume_divergence = _latest_price_volume_divergence(
        points,
        pivots=pivot_lows,
        price_values=low_values,
        volume_values=volume_values,
        kind="bullish_price_volume_divergence",
        direction="low",
    )
    if bullish_volume_divergence is not None:
        events.append(bullish_volume_divergence)

    return events


def _latest_complete_point(points: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for point in reversed(points):
        if point["close"] is not None:
            return point
    return points[-1] if points else None


def _event(
    point: Dict[str, Any],
    *,
    kind: str,
    metric: str,
    severity: str,
    value: float,
    threshold: float,
    confidence: float,
    description: str,
) -> Dict[str, Any]:
    return {
        "type": kind,
        "metric": metric,
        "openTime": point["openTime"],
        "closeTime": point["closeTime"],
        "severity": severity,
        "confidence": _round_or_none(confidence, digits=4),
        "value": _round_or_none(value),
        "threshold": _round_or_none(threshold),
        "description": description,
    }


def _window_summary(
    *,
    highs: List[Optional[Decimal]],
    lows: List[Optional[Decimal]],
    volumes: List[Decimal],
    candles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    high_values = [value for value in highs if value is not None]
    low_values = [value for value in lows if value is not None]
    trade_count = sum(int(candle.get("tradeCount", 0)) for candle in candles)
    return {
        "high": _float_or_none(max(high_values) if high_values else None),
        "low": _float_or_none(min(low_values) if low_values else None),
        "baseVolume": _float_or_none(sum(volumes, Decimal("0"))),
        "tradeCount": trade_count,
    }


def _pivot_indices(
    values: List[Optional[float]],
    *,
    pivot_type: str,
) -> List[int]:
    pivots: List[int] = []
    for index in range(PIVOT_RADIUS, len(values) - PIVOT_RADIUS):
        center = values[index]
        if center is None:
            continue
        left = values[index - PIVOT_RADIUS:index]
        right = values[index + 1:index + PIVOT_RADIUS + 1]
        if any(value is None for value in [*left, *right]):
            continue
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


def _latest_double_pattern(
    points: List[Dict[str, Any]],
    *,
    pivots: List[int],
    edge_values: List[Optional[float]],
    middle_values: List[Optional[float]],
    kind: str,
    direction: str,
    middle_mode: str,
) -> Optional[Dict[str, Any]]:
    for left_index, right_index in zip(reversed(pivots[:-1]), reversed(pivots[1:])):
        span = right_index - left_index
        if span < MIN_PATTERN_SPAN or span > MAX_PATTERN_SPAN:
            continue

        left_value = edge_values[left_index]
        right_value = edge_values[right_index]
        if left_value is None or right_value is None:
            continue

        middle = [
            value
            for value in middle_values[left_index + 1:right_index]
            if value is not None
        ]
        if not middle:
            continue

        average_edge = (left_value + right_value) / 2
        if average_edge <= 0:
            continue

        edge_difference_pct = abs(left_value - right_value) / average_edge * 100
        if edge_difference_pct > DOUBLE_PATTERN_TOLERANCE_PCT:
            continue

        if middle_mode == "min":
            middle_reference = min(middle)
            structure_depth_pct = (average_edge - middle_reference) / average_edge * 100
        else:
            middle_reference = max(middle)
            structure_depth_pct = (middle_reference - average_edge) / average_edge * 100

        if structure_depth_pct < DOUBLE_PATTERN_DEPTH_PCT:
            continue

        confidence = 0.58
        confidence += min(
            0.18,
            max(0.0, DOUBLE_PATTERN_TOLERANCE_PCT - edge_difference_pct)
            / DOUBLE_PATTERN_TOLERANCE_PCT
            * 0.18,
        )
        confidence += min(
            0.18,
            structure_depth_pct / (DOUBLE_PATTERN_DEPTH_PCT * 3) * 0.18,
        )

        return _event(
            points[right_index],
            kind=kind,
            metric="pattern",
            severity=(
                "high"
                if structure_depth_pct >= DOUBLE_PATTERN_DEPTH_PCT * 2
                else "medium"
            ),
            value=edge_difference_pct,
            threshold=DOUBLE_PATTERN_TOLERANCE_PCT,
            confidence=min(0.99, confidence),
            description=(
                f"Two swing {direction} formed inside a {edge_difference_pct:.2f}% "
                f"band with {structure_depth_pct:.2f}% internal retrace."
            ),
        )
    return None


def _latest_rsi_divergence(
    points: List[Dict[str, Any]],
    *,
    pivots: List[int],
    price_values: List[Optional[float]],
    rsi_values: List[Optional[float]],
    kind: str,
    direction: str,
) -> Optional[Dict[str, Any]]:
    for left_index, right_index in zip(reversed(pivots[:-1]), reversed(pivots[1:])):
        span = right_index - left_index
        if span < MIN_PATTERN_SPAN or span > MAX_PATTERN_SPAN:
            continue

        left_price = price_values[left_index]
        right_price = price_values[right_index]
        left_rsi = rsi_values[left_index]
        right_rsi = rsi_values[right_index]
        if None in (left_price, right_price, left_rsi, right_rsi):
            continue

        assert left_price is not None
        assert right_price is not None
        assert left_rsi is not None
        assert right_rsi is not None
        if left_price <= 0 or right_price <= 0:
            continue

        if direction == "high":
            price_move_pct = (right_price - left_price) / left_price * 100
            rsi_move = left_rsi - right_rsi
            valid = (
                price_move_pct >= DIVERGENCE_PRICE_MOVE_PCT
                and rsi_move >= DIVERGENCE_RSI_DELTA
            )
            description = (
                f"Price pushed to a higher high (+{price_move_pct:.2f}%) while RSI "
                f"faded by {rsi_move:.2f} points."
            )
        else:
            price_move_pct = (left_price - right_price) / left_price * 100
            rsi_move = right_rsi - left_rsi
            valid = (
                price_move_pct >= DIVERGENCE_PRICE_MOVE_PCT
                and rsi_move >= DIVERGENCE_RSI_DELTA
            )
            description = (
                f"Price printed a lower low (-{price_move_pct:.2f}%) while RSI "
                f"improved by {rsi_move:.2f} points."
            )

        if not valid:
            continue

        confidence = 0.56
        confidence += min(
            0.18,
            price_move_pct / (DIVERGENCE_PRICE_MOVE_PCT * 4) * 0.18,
        )
        confidence += min(
            0.18,
            rsi_move / (DIVERGENCE_RSI_DELTA * 3) * 0.18,
        )

        return _event(
            points[right_index],
            kind=kind,
            metric="rsi",
            severity=(
                "high"
                if price_move_pct >= DIVERGENCE_PRICE_MOVE_PCT * 2
                and rsi_move >= DIVERGENCE_RSI_DELTA * 1.5
                else "medium"
            ),
            value=rsi_move,
            threshold=DIVERGENCE_RSI_DELTA,
            confidence=min(0.99, confidence),
            description=description,
        )
    return None


def _latest_price_volume_divergence(
    points: List[Dict[str, Any]],
    *,
    pivots: List[int],
    price_values: List[Optional[float]],
    volume_values: List[Optional[float]],
    kind: str,
    direction: str,
) -> Optional[Dict[str, Any]]:
    for left_index, right_index in zip(reversed(pivots[:-1]), reversed(pivots[1:])):
        span = right_index - left_index
        if span < MIN_PATTERN_SPAN or span > MAX_PATTERN_SPAN:
            continue

        left_price = price_values[left_index]
        right_price = price_values[right_index]
        left_volume = volume_values[left_index]
        right_volume = volume_values[right_index]
        if None in (left_price, right_price, left_volume, right_volume):
            continue

        assert left_price is not None
        assert right_price is not None
        assert left_volume is not None
        assert right_volume is not None
        if left_price <= 0 or left_volume <= 0:
            continue

        if direction == "high":
            price_move_pct = (right_price - left_price) / left_price * 100
            valid_price = price_move_pct >= DIVERGENCE_PRICE_MOVE_PCT
            direction_text = f"higher high (+{price_move_pct:.2f}%)"
        else:
            price_move_pct = (left_price - right_price) / left_price * 100
            valid_price = price_move_pct >= DIVERGENCE_PRICE_MOVE_PCT
            direction_text = f"lower low (-{price_move_pct:.2f}%)"

        volume_change_pct = (right_volume - left_volume) / left_volume * 100
        valid_volume = volume_change_pct <= -DIVERGENCE_VOLUME_DROP_PCT
        if not (valid_price and valid_volume):
            continue

        confidence = 0.54
        confidence += min(
            0.18,
            price_move_pct / (DIVERGENCE_PRICE_MOVE_PCT * 4) * 0.18,
        )
        confidence += min(
            0.22,
            abs(volume_change_pct) / (DIVERGENCE_VOLUME_DROP_PCT * 4) * 0.22,
        )

        return _event(
            points[right_index],
            kind=kind,
            metric="baseVolume",
            severity=(
                "high"
                if abs(volume_change_pct) >= DIVERGENCE_VOLUME_DROP_PCT * 1.5
                else "medium"
            ),
            value=volume_change_pct,
            threshold=-DIVERGENCE_VOLUME_DROP_PCT,
            confidence=min(0.99, confidence),
            description=(
                f"Price made a {direction_text} while pivot volume fell "
                f"{abs(volume_change_pct):.2f}%."
            ),
        )
    return None


def _decimal_or_none(value: object) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_or_zero(value: object) -> Decimal:
    parsed = _decimal_or_none(value)
    return parsed if parsed is not None else Decimal("0")


def _float_or_none(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _log_return(
    previous_close: Optional[Decimal],
    close: Optional[Decimal],
) -> Optional[float]:
    if previous_close is None or close is None:
        return None
    if previous_close <= 0 or close <= 0:
        return None
    return math.log(float(close / previous_close))


def _realized_volatility(
    log_returns: List[Optional[float]],
    index: int,
    window: int,
) -> Optional[float]:
    if index < window:
        return None
    values = log_returns[index - window + 1:index + 1]
    if any(value is None for value in values):
        return None
    return math.sqrt(sum(float(value) ** 2 for value in values)) * 100


def _parkinson_volatility(
    highs: List[Optional[Decimal]],
    lows: List[Optional[Decimal]],
    index: int,
    window: int,
) -> Optional[float]:
    if index + 1 < window:
        return None
    high_window = highs[index - window + 1:index + 1]
    low_window = lows[index - window + 1:index + 1]
    terms: List[float] = []
    for high, low in zip(high_window, low_window):
        if high is None or low is None or high <= 0 or low <= 0:
            return None
        terms.append(math.log(float(high / low)) ** 2)
    if not terms:
        return None
    variance = sum(terms) / (4 * len(terms) * math.log(2))
    return math.sqrt(max(0.0, variance)) * 100


def _garman_klass_volatility(
    opens: List[Optional[Decimal]],
    highs: List[Optional[Decimal]],
    lows: List[Optional[Decimal]],
    closes: List[Optional[Decimal]],
    index: int,
    window: int,
) -> Optional[float]:
    if index + 1 < window:
        return None
    values: List[float] = []
    for open_, high, low, close in zip(
        opens[index - window + 1:index + 1],
        highs[index - window + 1:index + 1],
        lows[index - window + 1:index + 1],
        closes[index - window + 1:index + 1],
    ):
        if None in (open_, high, low, close):
            return None
        assert open_ is not None
        assert high is not None
        assert low is not None
        assert close is not None
        if open_ <= 0 or high <= 0 or low <= 0 or close <= 0:
            return None
        high_low = math.log(float(high / low))
        close_open = math.log(float(close / open_))
        values.append(
            0.5 * high_low ** 2
            - (2 * math.log(2) - 1) * close_open ** 2
        )
    if not values:
        return None
    variance = sum(values) / len(values)
    return math.sqrt(max(0.0, variance)) * 100


def _rsi(
    closes: List[Optional[Decimal]],
    index: int,
    period: int,
) -> Optional[float]:
    if index < period:
        return None
    values = closes[index - period:index + 1]
    if any(value is None for value in values):
        return None

    gains = Decimal("0")
    losses = Decimal("0")
    for previous, current in zip(values, values[1:]):
        assert previous is not None
        assert current is not None
        change = current - previous
        if change > 0:
            gains += change
        else:
            losses += abs(change)

    if gains == 0 and losses == 0:
        return 50.0
    if losses == 0:
        return 100.0
    relative_strength = gains / losses
    return float(Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength)))


def _momentum(
    closes: List[Optional[Decimal]],
    index: int,
    period: int,
) -> Optional[float]:
    if index < period:
        return None
    current = closes[index]
    previous = closes[index - period]
    if current is None or previous is None or previous == 0:
        return None
    return float(((current - previous) / previous) * Decimal("100"))


def _mean_reversion(
    closes: List[Optional[Decimal]],
    index: int,
    window: int,
) -> Optional[Dict[str, float]]:
    if index + 1 < window:
        return None
    current = closes[index]
    if current is None:
        return None
    values = closes[index - window + 1:index + 1]
    if any(value is None for value in values):
        return None
    numeric_values = [float(value) for value in values if value is not None]
    mean = sum(numeric_values) / len(numeric_values)
    if mean == 0:
        return None
    variance = sum((value - mean) ** 2 for value in numeric_values) / len(
        numeric_values
    )
    stddev = math.sqrt(variance)
    if stddev == 0:
        z_score = 0.0
    else:
        z_score = (float(current) - mean) / stddev
    distance_pct = (float(current) - mean) / mean * 100
    return {"z_score": z_score, "distance_pct": distance_pct}


def _price_volume_divergence(
    closes: List[Optional[Decimal]],
    volumes: List[Decimal],
    index: int,
    period: int,
) -> Optional[float]:
    if index < period:
        return None
    current_close = closes[index]
    previous_close = closes[index - period]
    current_volume = volumes[index]
    previous_volume = volumes[index - period]
    if (
        current_close is None
        or previous_close is None
        or previous_close <= 0
        or previous_volume <= 0
    ):
        return None
    price_move_pct = abs(
        float((current_close - previous_close) / previous_close * Decimal("100"))
    )
    volume_change_pct = float(
        (current_volume - previous_volume) / previous_volume * Decimal("100")
    )
    if (
        price_move_pct < DIVERGENCE_PRICE_MOVE_PCT
        or volume_change_pct > -DIVERGENCE_VOLUME_DROP_PCT
    ):
        return None
    return volume_change_pct


def _volume_spike_ratio(
    volumes: List[Decimal],
    index: int,
    window: int,
) -> Optional[float]:
    if index < window:
        return None
    baseline_values = volumes[index - window:index]
    baseline = sum(baseline_values, Decimal("0")) / Decimal(window)
    if baseline <= 0:
        return None
    return float(volumes[index] / baseline)


def _vwap_deviation(
    close: Optional[Decimal],
    vwap: Optional[Decimal],
) -> Optional[float]:
    if close is None or vwap is None or vwap == 0:
        return None
    return float(((close - vwap) / vwap) * Decimal("100"))


def _round_or_none(value: Optional[float], digits: int = 6) -> Optional[float]:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def compute_return_correlation(
    target_candles: Iterable[Dict[str, Any]],
    peer_candles: Iterable[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    target_returns = _aligned_log_returns(target_candles)
    peer_returns = _aligned_log_returns(peer_candles)
    common_times = sorted(set(target_returns).intersection(peer_returns))
    if len(common_times) < 3:
        return None

    target_values = [target_returns[time] for time in common_times]
    peer_values = [peer_returns[time] for time in common_times]
    correlation = _pearson_correlation(target_values, peer_values)
    if correlation is None:
        return None
    return {
        "correlation": _round_or_none(correlation, digits=6),
        "sampleSize": len(common_times),
    }


def _aligned_log_returns(candles: Iterable[Dict[str, Any]]) -> Dict[int, float]:
    ordered = sorted(candles, key=lambda candle: int(candle["openTime"]))
    values: Dict[int, float] = {}
    previous_close: Optional[Decimal] = None
    for candle in ordered:
        close = _decimal_or_none(candle.get("close"))
        log_return = _log_return(previous_close, close)
        if log_return is not None:
            values[int(candle["openTime"])] = log_return
        previous_close = close
    return values


def _pearson_correlation(
    left: List[float],
    right: List[float],
) -> Optional[float]:
    if len(left) != len(right) or len(left) < 3:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right)
    )
    left_variance = sum((value - left_mean) ** 2 for value in left)
    right_variance = sum((value - right_mean) ** 2 for value in right)
    denominator = math.sqrt(left_variance * right_variance)
    if denominator == 0:
        return None
    return numerator / denominator
