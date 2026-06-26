from __future__ import annotations

import math
import random
from dataclasses import dataclass
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
class DatasetExample:
    label: str
    candles: List[Dict[str, float | int | str]]


def generate_dataset(
    *,
    labels: Sequence[str],
    samples_per_class: int,
    window_size: int,
    seed: int,
) -> List[DatasetExample]:
    rng = random.Random(seed)
    examples: List[DatasetExample] = []

    for label in labels:
        if label not in LABELS:
            raise ValueError(f"Unsupported synthetic label: {label}")
        for _ in range(samples_per_class):
            closes = _generate_close_path(label, window_size, rng)
            candles = _closes_to_candles(closes, rng=rng)
            examples.append(DatasetExample(label=label, candles=candles))

    rng.shuffle(examples)
    return examples


def _generate_close_path(
    label: str,
    window_size: int,
    rng: random.Random,
) -> List[float]:
    base = rng.uniform(90.0, 115.0)
    scale = rng.uniform(0.85, 1.2)

    if label == "head_and_shoulders":
        points = [
            (0.00, base),
            (0.16, base + 4.0 * scale),
            (0.28, base + 0.8 * scale),
            (0.48, base + 9.0 * scale),
            (0.62, base + 1.2 * scale),
            (0.78, base + 4.2 * scale),
            (1.00, base - 2.5 * scale),
        ]
        path = _interpolate(points, window_size)
    elif label == "double_top":
        points = [
            (0.00, base),
            (0.24, base + 7.5 * scale),
            (0.48, base + 1.2 * scale),
            (0.72, base + rng.uniform(7.0, 8.1) * scale),
            (1.00, base - 1.5 * scale),
        ]
        path = _interpolate(points, window_size)
    elif label == "double_bottom":
        points = [
            (0.00, base),
            (0.24, base - 7.5 * scale),
            (0.48, base - 1.2 * scale),
            (0.72, base - rng.uniform(7.0, 8.1) * scale),
            (1.00, base + 1.5 * scale),
        ]
        path = _interpolate(points, window_size)
    elif label == "triangle":
        path = _triangle_path(base, scale, window_size, rng)
    elif label == "flag":
        path = _flag_path(base, scale, window_size, rng)
    else:
        path = _random_walk(base, window_size, rng)

    return _add_market_noise(path, rng=rng, strength=0.18 * scale)


def _interpolate(points: Sequence[tuple[float, float]], length: int) -> List[float]:
    indexed = [
        (min(length - 1, max(0, round(position * (length - 1)))), value)
        for position, value in points
    ]
    indexed = sorted(dict(indexed).items())
    output = [indexed[0][1]] * length

    for (left_index, left_value), (right_index, right_value) in zip(
        indexed,
        indexed[1:],
    ):
        span = max(1, right_index - left_index)
        for index in range(left_index, right_index + 1):
            progress = (index - left_index) / span
            eased = progress * progress * (3 - 2 * progress)
            output[index] = left_value + (right_value - left_value) * eased

    return output


def _triangle_path(
    base: float,
    scale: float,
    length: int,
    rng: random.Random,
) -> List[float]:
    drift = rng.uniform(-1.0, 1.0) * scale
    phase = rng.uniform(0.0, math.pi)
    values: List[float] = []
    for index in range(length):
        progress = index / (length - 1)
        amplitude = (6.5 * (1.0 - progress) + 0.8) * scale
        center = base + drift * progress
        wave = math.sin(progress * math.pi * 6.0 + phase)
        values.append(center + amplitude * wave)
    return values


def _flag_path(
    base: float,
    scale: float,
    length: int,
    rng: random.Random,
) -> List[float]:
    impulse_end = max(12, length // 4)
    impulse = rng.choice([-1.0, 1.0]) * rng.uniform(8.0, 11.0) * scale
    path: List[float] = []
    for index in range(length):
        if index <= impulse_end:
            progress = index / impulse_end
            path.append(base + impulse * progress)
        else:
            progress = (index - impulse_end) / (length - impulse_end - 1)
            channel = -0.28 * impulse * progress
            wave = math.sin(progress * math.pi * 5.0) * 0.9 * scale
            path.append(base + impulse + channel + wave)
    return path


def _random_walk(base: float, length: int, rng: random.Random) -> List[float]:
    values = [base]
    drift = rng.uniform(-0.035, 0.035)
    volatility = rng.uniform(0.35, 0.9)
    for _ in range(1, length):
        values.append(max(1.0, values[-1] + drift + rng.gauss(0.0, volatility)))
    return values


def _add_market_noise(
    path: Sequence[float],
    *,
    rng: random.Random,
    strength: float,
) -> List[float]:
    noisy: List[float] = []
    carry = 0.0
    for value in path:
        carry = carry * 0.55 + rng.gauss(0.0, strength)
        noisy.append(max(1.0, value + carry))
    return noisy


def _closes_to_candles(
    closes: Sequence[float],
    *,
    rng: random.Random,
) -> List[Dict[str, float | int | str]]:
    candles: List[Dict[str, float | int | str]] = []
    previous_close = closes[0] + rng.gauss(0.0, 0.25)
    base_volume = rng.uniform(80.0, 250.0)

    for index, close in enumerate(closes):
        open_price = previous_close
        body_high = max(open_price, close)
        body_low = min(open_price, close)
        wick_scale = max(0.04, abs(close - open_price) * 0.25)
        high = body_high + abs(rng.gauss(0.12, wick_scale))
        low = max(0.01, body_low - abs(rng.gauss(0.12, wick_scale)))
        volume = max(1.0, base_volume * rng.uniform(0.65, 1.55))
        quote_volume = volume * close
        trade_count = max(1, int(volume * rng.uniform(0.3, 1.2)))

        candles.append(
            {
                "openTime": index * 60_000,
                "closeTime": (index + 1) * 60_000,
                "open": round(open_price, 8),
                "high": round(high, 8),
                "low": round(low, 8),
                "close": round(close, 8),
                "baseVolume": round(volume, 8),
                "quoteVolume": round(quote_volume, 8),
                "tradeCount": trade_count,
                "timeframe": "1m",
                "status": "complete",
            }
        )
        previous_close = close

    return candles


def dataset_summary(examples: Iterable[DatasetExample]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for example in examples:
        counts[example.label] = counts.get(example.label, 0) + 1
    return dict(sorted(counts.items()))
