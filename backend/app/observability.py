from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal
from math import isfinite
from threading import RLock
from typing import Any, Deque, Dict, Iterable, Mapping, Optional, Tuple

from .models import Trade


LATENCY_BUCKETS_MS = (
    1,
    2,
    5,
    10,
    25,
    50,
    100,
    250,
    500,
    1_000,
    2_000,
    5_000,
    10_000,
    30_000,
    60_000,
    120_000,
)
RECENT_SAMPLE_LIMIT = 600
LatencyKey = Tuple[str, str, str, str, str]
MarketKey = Tuple[str, str]
DisplayKey = Tuple[str, str, str, str]


@dataclass
class RollingLatency:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    buckets: Dict[float, int] = field(
        default_factory=lambda: {float(bucket): 0 for bucket in LATENCY_BUCKETS_MS}
    )
    recent: Deque[float] = field(
        default_factory=lambda: deque(maxlen=RECENT_SAMPLE_LIMIT)
    )

    def observe(self, value_ms: Optional[float]) -> bool:
        value = _finite_float(value_ms)
        if value is None or value < 0:
            return False

        self.count += 1
        self.total_ms += value
        self.max_ms = max(self.max_ms, value)
        self.recent.append(value)
        for bucket in LATENCY_BUCKETS_MS:
            if value <= bucket:
                self.buckets[float(bucket)] += 1
        return True

    def average_ms(self) -> Optional[float]:
        if self.count == 0:
            return None
        return self.total_ms / self.count

    def quantile(self, fraction: float) -> Optional[float]:
        if not self.recent:
            return None
        values = sorted(self.recent)
        index = min(
            len(values) - 1,
            max(0, round((len(values) - 1) * fraction)),
        )
        return values[index]


@dataclass
class LatestMarket:
    price: Optional[float] = None
    exchange_timestamp_ms: Optional[int] = None
    received_timestamp_ms: Optional[int] = None
    processed_timestamp_ms: Optional[int] = None
    latency_ms: Optional[int] = None
    trade_count: int = 0


@dataclass
class LatestDisplay:
    channel: str
    exchange: str
    instrument_id: str
    timeframe: str
    price: Optional[float]
    data_timestamp_ms: Optional[int]
    backend_generated_at_ms: Optional[int]
    frontend_received_at_ms: Optional[int]
    displayed_at_ms: int
    accepted_at_ms: int


class LatencyObservability:
    def __init__(self) -> None:
        self._lock = RLock()
        self._latency: Dict[LatencyKey, RollingLatency] = defaultdict(RollingLatency)
        self._latest_markets: Dict[MarketKey, LatestMarket] = {}
        self._latest_displays: Dict[DisplayKey, LatestDisplay] = {}
        self._frontend_samples_total = 0
        self._chart_lag_ms: Dict[DisplayKey, float] = {}

    def observe_trade(self, trade: Trade, processed_at_ms: int) -> None:
        exchange = _label_value(trade.exchange)
        instrument_id = _label_value(trade.instrument_id)
        price = _decimal_to_float(trade.price)
        queue_delay_ms = max(0, processed_at_ms - trade.received_timestamp_ms)

        with self._lock:
            self._latest_markets[(exchange, instrument_id)] = LatestMarket(
                price=price,
                exchange_timestamp_ms=trade.exchange_timestamp_ms,
                received_timestamp_ms=trade.received_timestamp_ms,
                processed_timestamp_ms=processed_at_ms,
                latency_ms=trade.latency_ms,
                trade_count=(
                    self._latest_markets.get(
                        (exchange, instrument_id),
                        LatestMarket(),
                    ).trade_count
                    + 1
                ),
            )
            self._observe_locked(
                stage="exchange_to_backend",
                channel="market",
                exchange=exchange,
                instrument_id=instrument_id,
                timeframe="",
                value_ms=trade.latency_ms,
            )
            self._observe_locked(
                stage="backend_queue",
                channel="market",
                exchange=exchange,
                instrument_id=instrument_id,
                timeframe="",
                value_ms=queue_delay_ms,
            )

    def observe_metrics_snapshot(self, response: Mapping[str, Any]) -> None:
        exchange = _label_value(response.get("exchange"))
        instrument_id = _label_value(response.get("instrumentId"))
        timeframe = _label_value(response.get("timeframe"))
        latency = _mapping_or_empty(response.get("metricsLatency"))
        window_name = _label_value(latency.get("windowName") or "default")
        channel = f"metrics_{window_name}" if window_name else "metrics"

        with self._lock:
            self._observe_locked(
                stage="backend_compute",
                channel=channel,
                exchange=exchange,
                instrument_id=instrument_id,
                timeframe=timeframe,
                value_ms=_finite_float(latency.get("computeDurationMs")),
            )
            self._observe_locked(
                stage="data_freshness",
                channel=channel,
                exchange=exchange,
                instrument_id=instrument_id,
                timeframe=timeframe,
                value_ms=_finite_float(latency.get("effectiveLagMs")),
            )

    def observe_chart_snapshot(
        self,
        channel: str,
        response: Mapping[str, Any],
    ) -> None:
        exchange = _label_value(response.get("exchange"))
        instrument_id = _label_value(response.get("instrumentId"))
        timeframe = _label_value(response.get("timeframe"))
        latency = _mapping_or_empty(response.get("chartLatency"))
        effective_lag_ms = _finite_float(latency.get("effectiveLagMs"))

        with self._lock:
            key = (
                _label_value(channel),
                exchange,
                instrument_id,
                timeframe,
            )
            if effective_lag_ms is not None:
                self._chart_lag_ms[key] = effective_lag_ms
            self._observe_locked(
                stage="data_freshness",
                channel=channel,
                exchange=exchange,
                instrument_id=instrument_id,
                timeframe=timeframe,
                value_ms=effective_lag_ms,
            )

    def observe_frontend_display(
        self,
        samples: Iterable[Mapping[str, Any]],
        accepted_at_ms: int,
    ) -> int:
        accepted = 0
        with self._lock:
            for sample in samples:
                channel = _label_value(sample.get("channel") or "unknown")
                exchange = _label_value(sample.get("exchange"))
                instrument_id = _label_value(sample.get("instrumentId"))
                timeframe = _label_value(sample.get("timeframe"))
                displayed_at_ms = _int_or_none(sample.get("displayedAt"))
                if (
                    not channel
                    or not exchange
                    or not instrument_id
                    or displayed_at_ms is None
                ):
                    continue

                frontend_received_at_ms = _int_or_none(sample.get("frontendReceivedAt"))
                backend_generated_at_ms = _int_or_none(sample.get("backendGeneratedAt"))
                backend_received_at_ms = _int_or_none(sample.get("backendReceivedAt"))
                exchange_timestamp_ms = _int_or_none(sample.get("exchangeTimestamp"))
                data_timestamp_ms = _int_or_none(sample.get("dataTimestamp"))
                price = _finite_float(sample.get("price"))
                data_anchor_ms = data_timestamp_ms or exchange_timestamp_ms

                self._latest_displays[(channel, exchange, instrument_id, timeframe)] = (
                    LatestDisplay(
                        channel=channel,
                        exchange=exchange,
                        instrument_id=instrument_id,
                        timeframe=timeframe,
                        price=price,
                        data_timestamp_ms=data_anchor_ms,
                        backend_generated_at_ms=backend_generated_at_ms,
                        frontend_received_at_ms=frontend_received_at_ms,
                        displayed_at_ms=displayed_at_ms,
                        accepted_at_ms=accepted_at_ms,
                    )
                )

                if price is not None and channel == "markets":
                    market = self._latest_markets.setdefault(
                        (exchange, instrument_id),
                        LatestMarket(),
                    )
                    market.price = price

                self._observe_locked(
                    stage="backend_to_frontend",
                    channel=channel,
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    value_ms=_delta_ms(
                        frontend_received_at_ms, backend_generated_at_ms
                    ),
                )
                self._observe_locked(
                    stage="frontend_render",
                    channel=channel,
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    value_ms=_delta_ms(displayed_at_ms, frontend_received_at_ms),
                )
                self._observe_locked(
                    stage="backend_to_display",
                    channel=channel,
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    value_ms=_delta_ms(displayed_at_ms, backend_received_at_ms),
                )
                self._observe_locked(
                    stage="exchange_to_display",
                    channel=channel,
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    value_ms=_delta_ms(displayed_at_ms, exchange_timestamp_ms),
                )
                self._observe_locked(
                    stage="data_to_display",
                    channel=channel,
                    exchange=exchange,
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    value_ms=_delta_ms(displayed_at_ms, data_anchor_ms),
                )
                accepted += 1

            self._frontend_samples_total += accepted
        return accepted

    def health_summary(self) -> Dict[str, object]:
        with self._lock:
            return {
                "latencySeries": len(self._latency),
                "latestMarkets": len(self._latest_markets),
                "latestDisplays": len(self._latest_displays),
                "frontendSamples": self._frontend_samples_total,
                "prometheusPath": "/metrics",
                "latencyApiPath": "/api/v1/observability/latency",
            }

    def snapshot(self, now_ms: int) -> Dict[str, object]:
        with self._lock:
            latency = [
                self._latency_summary(key, stats)
                for key, stats in sorted(self._latency.items())
            ]
            markets = [
                {
                    "exchange": exchange,
                    "instrumentId": instrument_id,
                    "price": market.price,
                    "exchangeTimestamp": market.exchange_timestamp_ms,
                    "receivedTimestamp": market.received_timestamp_ms,
                    "processedTimestamp": market.processed_timestamp_ms,
                    "tradeLatencyMs": market.latency_ms,
                    "ageMs": _delta_ms(now_ms, market.received_timestamp_ms),
                    "tradeCount": market.trade_count,
                }
                for (exchange, instrument_id), market in sorted(
                    self._latest_markets.items()
                )
            ]
            displays = [
                {
                    "channel": display.channel,
                    "exchange": display.exchange,
                    "instrumentId": display.instrument_id,
                    "timeframe": display.timeframe or None,
                    "price": display.price,
                    "dataTimestamp": display.data_timestamp_ms,
                    "backendGeneratedAt": display.backend_generated_at_ms,
                    "frontendReceivedAt": display.frontend_received_at_ms,
                    "displayedAt": display.displayed_at_ms,
                    "acceptedAt": display.accepted_at_ms,
                    "sampleAgeMs": max(0, now_ms - display.accepted_at_ms),
                }
                for display in sorted(
                    self._latest_displays.values(),
                    key=lambda item: (
                        item.channel,
                        item.exchange,
                        item.instrument_id,
                        item.timeframe,
                    ),
                )
            ]

        return {
            "generatedAt": now_ms,
            "frontendSamples": self._frontend_samples_total,
            "latency": latency,
            "markets": markets,
            "displays": displays,
            "prometheusPath": "/metrics",
            "grafanaDashboard": "/d/tickframe-latency/tickframe-latency",
            "limits": {
                "recentSamplesPerSeries": RECENT_SAMPLE_LIMIT,
                "histogramBucketsMs": list(LATENCY_BUCKETS_MS),
            },
        }

    def prometheus_text(self, now_ms: int) -> str:
        with self._lock:
            latency_items = list(sorted(self._latency.items()))
            market_items = list(sorted(self._latest_markets.items()))
            display_items = list(sorted(self._latest_displays.items()))
            chart_lag_items = list(sorted(self._chart_lag_ms.items()))
            frontend_samples_total = self._frontend_samples_total

        lines = [
            "# HELP tickframe_latency_ms Latency measurements across the Tickframe live-data pipeline.",
            "# TYPE tickframe_latency_ms histogram",
        ]
        for key, stats in latency_items:
            labels = _latency_labels(key)
            for bucket in LATENCY_BUCKETS_MS:
                bucket_labels = {**labels, "le": _bucket_label(bucket)}
                lines.append(
                    f"tickframe_latency_ms_bucket{_labels(bucket_labels)} "
                    f"{stats.buckets[float(bucket)]}"
                )
            lines.append(
                f"tickframe_latency_ms_bucket{_labels({**labels, 'le': '+Inf'})} "
                f"{stats.count}"
            )
            lines.append(
                f"tickframe_latency_ms_sum{_labels(labels)} {_number(stats.total_ms)}"
            )
            lines.append(f"tickframe_latency_ms_count{_labels(labels)} {stats.count}")

        lines.extend(
            [
                "# HELP tickframe_latency_recent_ms Rolling recent latency quantiles computed in the backend process.",
                "# TYPE tickframe_latency_recent_ms gauge",
            ]
        )
        for key, stats in latency_items:
            labels = _latency_labels(key)
            for quantile, value in (
                ("p50", stats.quantile(0.50)),
                ("p95", stats.quantile(0.95)),
                ("p99", stats.quantile(0.99)),
            ):
                if value is None:
                    continue
                lines.append(
                    "tickframe_latency_recent_ms"
                    f"{_labels({**labels, 'quantile': quantile})} "
                    f"{_number(value)}"
                )

        lines.extend(
            [
                "# HELP tickframe_latest_price Latest observed public trade price by source.",
                "# TYPE tickframe_latest_price gauge",
            ]
        )
        for (exchange, instrument_id), market in market_items:
            if market.price is None:
                continue
            lines.append(
                "tickframe_latest_price"
                f"{_labels({'exchange': exchange, 'instrument_id': instrument_id})} "
                f"{_number(market.price)}"
            )

        lines.extend(
            [
                "# HELP tickframe_latest_trade_age_ms Age of the latest backend-received trade.",
                "# TYPE tickframe_latest_trade_age_ms gauge",
            ]
        )
        for (exchange, instrument_id), market in market_items:
            age_ms = _delta_ms(now_ms, market.received_timestamp_ms)
            if age_ms is None:
                continue
            lines.append(
                "tickframe_latest_trade_age_ms"
                f"{_labels({'exchange': exchange, 'instrument_id': instrument_id})} "
                f"{_number(age_ms)}"
            )

        lines.extend(
            [
                "# HELP tickframe_chart_lag_ms Latest chart or metrics data freshness lag.",
                "# TYPE tickframe_chart_lag_ms gauge",
            ]
        )
        for (channel, exchange, instrument_id, timeframe), value in chart_lag_items:
            lines.append(
                "tickframe_chart_lag_ms"
                f"{_labels({'channel': channel, 'exchange': exchange, 'instrument_id': instrument_id, 'timeframe': timeframe})} "
                f"{_number(value)}"
            )

        lines.extend(
            [
                "# HELP tickframe_frontend_display_samples_total Accepted frontend display telemetry samples.",
                "# TYPE tickframe_frontend_display_samples_total counter",
                f"tickframe_frontend_display_samples_total {frontend_samples_total}",
                "# HELP tickframe_frontend_last_display_age_ms Age of the latest accepted display telemetry sample.",
                "# TYPE tickframe_frontend_last_display_age_ms gauge",
            ]
        )
        for (
            channel,
            exchange,
            instrument_id,
            timeframe,
        ), display in display_items:
            lines.append(
                "tickframe_frontend_last_display_age_ms"
                f"{_labels({'channel': channel, 'exchange': exchange, 'instrument_id': instrument_id, 'timeframe': timeframe})} "
                f"{_number(max(0, now_ms - display.accepted_at_ms))}"
            )

        return "\n".join(lines) + "\n"

    def _observe_locked(
        self,
        *,
        stage: str,
        channel: str,
        exchange: str,
        instrument_id: str,
        timeframe: str,
        value_ms: Optional[float],
    ) -> None:
        if _finite_float(value_ms) is None:
            return
        key = (
            _label_value(stage),
            _label_value(channel),
            _label_value(exchange),
            _label_value(instrument_id),
            _label_value(timeframe),
        )
        self._latency[key].observe(value_ms)

    @staticmethod
    def _latency_summary(
        key: LatencyKey,
        stats: RollingLatency,
    ) -> Dict[str, object]:
        stage, channel, exchange, instrument_id, timeframe = key
        return {
            "stage": stage,
            "channel": channel,
            "exchange": exchange,
            "instrumentId": instrument_id,
            "timeframe": timeframe or None,
            "count": stats.count,
            "avgMs": _round_or_none(stats.average_ms()),
            "maxMs": _round_or_none(stats.max_ms if stats.count else None),
            "p50Ms": _round_or_none(stats.quantile(0.50)),
            "p95Ms": _round_or_none(stats.quantile(0.95)),
            "p99Ms": _round_or_none(stats.quantile(0.99)),
        }


def service_prometheus_text(
    *,
    collectors: Mapping[str, Mapping[str, Any]],
    pipeline: Mapping[str, Any],
    metrics: Mapping[str, Any],
    database: Mapping[str, Any],
) -> str:
    lines = [
        "# HELP tickframe_collector_connected Whether an exchange collector is connected.",
        "# TYPE tickframe_collector_connected gauge",
    ]
    for exchange, collector in sorted(collectors.items()):
        labels = _labels({"exchange": exchange})
        connected = 1 if collector.get("connected") else 0
        lines.append(f"tickframe_collector_connected{labels} {connected}")

    lines.extend(
        [
            "# HELP tickframe_collector_message_age_ms Age of the last collector message.",
            "# TYPE tickframe_collector_message_age_ms gauge",
        ]
    )
    for exchange, collector in sorted(collectors.items()):
        message_age_ms = _finite_float(collector.get("messageAgeMs"))
        if message_age_ms is None:
            continue
        lines.append(
            "tickframe_collector_message_age_ms"
            f"{_labels({'exchange': exchange})} {_number(message_age_ms)}"
        )

    lines.extend(
        [
            "# HELP tickframe_collector_reconnects_total Collector reconnect attempts.",
            "# TYPE tickframe_collector_reconnects_total counter",
        ]
    )
    for exchange, collector in sorted(collectors.items()):
        reconnects = _finite_float(collector.get("reconnects")) or 0
        lines.append(
            "tickframe_collector_reconnects_total"
            f"{_labels({'exchange': exchange})} {_number(reconnects)}"
        )

    lines.extend(
        [
            "# HELP tickframe_pipeline_queue_size Current internal pipeline queue size.",
            "# TYPE tickframe_pipeline_queue_size gauge",
            f"tickframe_pipeline_queue_size {_number(pipeline.get('queueSize'))}",
            "# HELP tickframe_pipeline_processed_trades_total Processed trade count.",
            "# TYPE tickframe_pipeline_processed_trades_total counter",
            f"tickframe_pipeline_processed_trades_total {_number(pipeline.get('processedTrades'))}",
            "# HELP tickframe_pipeline_revised_candles_total Revised candle count.",
            "# TYPE tickframe_pipeline_revised_candles_total counter",
            f"tickframe_pipeline_revised_candles_total {_number(pipeline.get('revisedCandles'))}",
            "# HELP tickframe_metrics_queue_size Current metrics worker queue size.",
            "# TYPE tickframe_metrics_queue_size gauge",
            f"tickframe_metrics_queue_size {_number(metrics.get('queueSize'))}",
            "# HELP tickframe_metrics_computed_snapshots_total Computed metric snapshots.",
            "# TYPE tickframe_metrics_computed_snapshots_total counter",
            f"tickframe_metrics_computed_snapshots_total {_number(metrics.get('computedSnapshots'))}",
            "# HELP tickframe_database_queue_size Current async database writer queue size.",
            "# TYPE tickframe_database_queue_size gauge",
            f"tickframe_database_queue_size {_number(database.get('queueSize'))}",
            "# HELP tickframe_database_written_trades_total Raw trades written to the database.",
            "# TYPE tickframe_database_written_trades_total counter",
            f"tickframe_database_written_trades_total {_number(database.get('writtenTrades'))}",
        ]
    )
    return "\n".join(lines) + "\n"


def _latency_labels(key: LatencyKey) -> Dict[str, str]:
    stage, channel, exchange, instrument_id, timeframe = key
    return {
        "stage": stage,
        "channel": channel,
        "exchange": exchange,
        "instrument_id": instrument_id,
        "timeframe": timeframe,
    }


def _mapping_or_empty(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _delta_ms(later: Optional[int], earlier: Optional[int]) -> Optional[int]:
    if later is None or earlier is None:
        return None
    return max(0, later - earlier)


def _int_or_none(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decimal_to_float(value: Decimal) -> Optional[float]:
    return _finite_float(str(value))


def _finite_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _label_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)[:120]


def _labels(values: Mapping[str, object]) -> str:
    if not values:
        return ""
    payload = ",".join(
        f'{key}="{_escape_label(value)}"' for key, value in sorted(values.items())
    )
    return f"{{{payload}}}"


def _escape_label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _bucket_label(value: int) -> str:
    return str(value)


def _number(value: object) -> str:
    number = _finite_float(value)
    if number is None:
        return "0"
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def _round_or_none(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 3)
