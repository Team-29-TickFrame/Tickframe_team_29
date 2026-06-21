from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional


TIMEFRAME_SECONDS: Dict[str, int] = {
    "1s": 1,
    "5s": 5,
    "15s": 15,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}
PERSISTED_TIMEFRAMES = {"1m", "5m", "15m", "1h"}
RUNTIME_TIMEFRAMES = {"5s", "15s"}
ONE_SECOND_RETENTION_MS = 14 * 24 * 60 * 60 * 1000


@dataclass(frozen=True)
class HistoryPage:
    candles: List[Dict[str, Any]]
    has_more: bool
    source: str


def timeframe_ms(timeframe: str) -> int:
    return TIMEFRAME_SECONDS[timeframe] * 1000


def resolve_time_range(
    *,
    timeframe: str,
    limit: int,
    now_ms: int,
    from_ms: Optional[int],
    to_ms: Optional[int],
) -> tuple[int, int]:
    bucket_ms = timeframe_ms(timeframe)
    resolved_to = to_ms if to_ms is not None else now_ms + bucket_ms
    if from_ms is not None and resolved_to <= from_ms:
        raise ValueError("'to' must be greater than 'from'")
    if from_ms is None:
        if timeframe in {"1s", "5s", "15s"}:
            resolved_from = max(0, resolved_to - ONE_SECOND_RETENTION_MS)
        else:
            resolved_from = 0
    else:
        resolved_from = from_ms

    resolved_from = (resolved_from // bucket_ms) * bucket_ms
    if resolved_to <= resolved_from:
        raise ValueError("'to' must be greater than 'from'")
    return resolved_from, resolved_to


def aggregate_memory_candles(
    candles: Iterable[Dict[str, Any]],
    *,
    timeframe: str,
    from_ms: int,
    to_ms: int,
    limit: int,
) -> HistoryPage:
    bucket_ms = timeframe_ms(timeframe)
    expected_count = TIMEFRAME_SECONDS[timeframe]
    grouped: Dict[int, List[Dict[str, Any]]] = {}

    for candle in candles:
        open_time = int(candle["openTime"])
        if open_time < from_ms or open_time >= to_ms:
            continue
        bucket = (open_time // bucket_ms) * bucket_ms
        grouped.setdefault(bucket, []).append(candle)

    values = [
        _aggregate_bucket(
            sorted(bucket_candles, key=lambda item: int(item["openTime"])),
            timeframe=timeframe,
            bucket_open_ms=bucket,
            bucket_ms=bucket_ms,
            expected_count=expected_count,
        )
        for bucket, bucket_candles in sorted(grouped.items())
    ]
    has_more = len(values) > limit
    if has_more:
        values = values[-limit:]
    return HistoryPage(candles=values, has_more=has_more, source="memory")


def _aggregate_bucket(
    candles: List[Dict[str, Any]],
    *,
    timeframe: str,
    bucket_open_ms: int,
    bucket_ms: int,
    expected_count: int,
) -> Dict[str, Any]:
    priced = [
        candle
        for candle in candles
        if all(candle.get(field) is not None for field in ("open", "high", "low", "close"))
    ]
    incomplete = (
        len(candles) < expected_count
        or any(candle.get("status") == "incomplete" for candle in candles)
    )
    recovered = any(candle.get("status") == "recovered" for candle in candles)
    trade_count = sum(int(candle["tradeCount"]) for candle in candles)

    if incomplete:
        status = "incomplete"
    elif recovered:
        status = "recovered"
    elif trade_count == 0:
        status = "complete_empty"
    else:
        status = "complete"

    first = priced[0] if priced else None
    last = priced[-1] if priced else None
    return {
        "exchange": candles[0]["exchange"],
        "marketType": candles[0]["marketType"],
        "instrumentId": candles[0]["instrumentId"],
        "timeframe": timeframe,
        "openTime": bucket_open_ms,
        "closeTime": bucket_open_ms + bucket_ms,
        "open": first["open"] if first else None,
        "high": _decimal_extreme(priced, "high", max),
        "low": _decimal_extreme(priced, "low", min),
        "close": last["close"] if last else None,
        "baseVolume": str(
            sum((Decimal(candle["baseVolume"]) for candle in candles), Decimal("0"))
        ),
        "quoteVolume": str(
            sum((Decimal(candle["quoteVolume"]) for candle in candles), Decimal("0"))
        ),
        "tradeCount": trade_count,
        "status": status,
        "revision": max(int(candle["revision"]) for candle in candles),
        "firstTradeId": first.get("firstTradeId") if first else None,
        "lastTradeId": last.get("lastTradeId") if last else None,
        "finalizedAt": max(int(candle["finalizedAt"]) for candle in candles),
    }


def _decimal_extreme(
    candles: List[Dict[str, Any]],
    field: str,
    operation: Any,
) -> Optional[str]:
    if not candles:
        return None
    return str(operation(Decimal(candle[field]) for candle in candles))
