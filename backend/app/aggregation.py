from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple, Union

from .models import Candle, Trade


SECOND_MS = 1000
StreamKey = Tuple[str, str, str]
CandleKey = Tuple[str, str, str, int]
TradeOrder = Tuple[int, int, Union[int, str]]


def candle_open_time(timestamp_ms: int) -> int:
    return timestamp_ms - (timestamp_ms % SECOND_MS)


def trade_order(trade: Trade) -> TradeOrder:
    try:
        normalized_id: Union[int, str] = int(trade.trade_id)
        id_type = 0
    except ValueError:
        normalized_id = trade.trade_id
        id_type = 1
    return (trade.exchange_timestamp_ms, id_type, normalized_id)


@dataclass
class _CandleState:
    exchange: str
    market_type: str
    instrument_id: str
    open_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    base_volume: Decimal
    quote_volume: Decimal
    trade_count: int
    first_trade_id: Optional[str]
    last_trade_id: Optional[str]
    first_order: TradeOrder
    last_order: TradeOrder
    revision: int = 1

    @classmethod
    def from_trade(cls, trade: Trade) -> "_CandleState":
        order = trade_order(trade)
        return cls(
            exchange=trade.exchange,
            market_type=trade.market_type,
            instrument_id=trade.instrument_id,
            open_time_ms=candle_open_time(trade.exchange_timestamp_ms),
            open=trade.price,
            high=trade.price,
            low=trade.price,
            close=trade.price,
            base_volume=trade.base_quantity,
            quote_volume=trade.quote_quantity,
            trade_count=1,
            first_trade_id=trade.trade_id,
            last_trade_id=trade.trade_id,
            first_order=order,
            last_order=order,
        )

    @classmethod
    def empty(
        cls,
        stream_key: StreamKey,
        open_time_ms: int,
        previous_close: Decimal,
    ) -> "_CandleState":
        exchange, market_type, instrument_id = stream_key
        empty_order: TradeOrder = (open_time_ms, 1, "")
        return cls(
            exchange=exchange,
            market_type=market_type,
            instrument_id=instrument_id,
            open_time_ms=open_time_ms,
            open=previous_close,
            high=previous_close,
            low=previous_close,
            close=previous_close,
            base_volume=Decimal("0"),
            quote_volume=Decimal("0"),
            trade_count=0,
            first_trade_id=None,
            last_trade_id=None,
            first_order=empty_order,
            last_order=empty_order,
        )

    def apply(self, trade: Trade) -> None:
        order = trade_order(trade)
        if self.trade_count == 0:
            self.open = trade.price
            self.high = trade.price
            self.low = trade.price
            self.close = trade.price
            self.base_volume = trade.base_quantity
            self.quote_volume = trade.quote_quantity
            self.trade_count = 1
            self.first_trade_id = trade.trade_id
            self.last_trade_id = trade.trade_id
            self.first_order = order
            self.last_order = order
            return

        if order < self.first_order:
            self.open = trade.price
            self.first_order = order
            self.first_trade_id = trade.trade_id
        if order > self.last_order:
            self.close = trade.price
            self.last_order = order
            self.last_trade_id = trade.trade_id

        self.high = max(self.high, trade.price)
        self.low = min(self.low, trade.price)
        self.base_volume += trade.base_quantity
        self.quote_volume += trade.quote_quantity
        self.trade_count += 1

    def finalize(self, finalized_at_ms: int, status: Optional[str] = None) -> Candle:
        resolved_status = status or (
            "complete" if self.trade_count else "complete_empty"
        )
        return Candle(
            exchange=self.exchange,
            market_type=self.market_type,
            instrument_id=self.instrument_id,
            timeframe="1s",
            open_time_ms=self.open_time_ms,
            close_time_ms=self.open_time_ms + SECOND_MS,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            base_volume=self.base_volume,
            quote_volume=self.quote_volume,
            trade_count=self.trade_count,
            status=resolved_status,
            revision=self.revision,
            first_trade_id=self.first_trade_id,
            last_trade_id=self.last_trade_id,
            finalized_at_ms=finalized_at_ms,
        )


class CandleAggregator:
    def __init__(
        self,
        allowed_lateness_ms: int = 2000,
        finalized_cache_size: int = 6000,
        dedup_cache_size: int = 200_000,
    ) -> None:
        self.allowed_lateness_ms = allowed_lateness_ms
        self.finalized_cache_size = finalized_cache_size
        self.dedup_cache_size = dedup_cache_size
        self._open: Dict[CandleKey, _CandleState] = {}
        self._finalized: "OrderedDict[CandleKey, _CandleState]" = OrderedDict()
        self._last_finalized_open: Dict[StreamKey, int] = {}
        self._last_close: Dict[StreamKey, Decimal] = {}
        self._gaps: Dict[StreamKey, List[Tuple[int, int]]] = {}
        self._seen_trades: "OrderedDict[Tuple[str, str, str, str], None]" = (
            OrderedDict()
        )

    def add_trade(self, trade: Trade, received_at_ms: int) -> Optional[Candle]:
        dedup_key = (
            trade.exchange,
            trade.market_type,
            trade.instrument_id,
            trade.trade_id,
        )
        if dedup_key in self._seen_trades:
            return None
        self._seen_trades[dedup_key] = None
        self._seen_trades.move_to_end(dedup_key)
        while len(self._seen_trades) > self.dedup_cache_size:
            self._seen_trades.popitem(last=False)

        open_time_ms = candle_open_time(trade.exchange_timestamp_ms)
        key = (*trade.stream_key, open_time_ms)
        finalized_state = self._finalized.get(key)
        if finalized_state is not None:
            finalized_state.apply(trade)
            finalized_state.revision += 1
            self._finalized.move_to_end(key)
            revised = finalized_state.finalize(received_at_ms, status="recovered")
            if self._last_finalized_open.get(trade.stream_key) == open_time_ms:
                self._last_close[trade.stream_key] = revised.close
            return revised

        last_finalized_open = self._last_finalized_open.get(trade.stream_key)
        if last_finalized_open is not None and open_time_ms <= last_finalized_open:
            recovered_state = _CandleState.from_trade(trade)
            recovered_state.revision = 2
            self._remember_finalized(key, recovered_state)
            recovered = recovered_state.finalize(
                received_at_ms,
                status="recovered",
            )
            if last_finalized_open == open_time_ms:
                self._last_close[trade.stream_key] = trade.price
            return recovered

        state = self._open.get(key)
        if state is None:
            self._open[key] = _CandleState.from_trade(trade)
        else:
            state.apply(trade)
        return None

    def finalize_due(
        self,
        now_ms: int,
        active_streams: Iterable[StreamKey],
    ) -> List[Candle]:
        watermark_ms = now_ms - self.allowed_lateness_ms
        last_due_open = candle_open_time(watermark_ms - 1)
        finalized: List[Candle] = []

        for stream_key in active_streams:
            start_open = self._next_open_time(stream_key)
            if start_open is None:
                trade_buckets = [
                    key[3]
                    for key in self._open
                    if key[:3] == stream_key and key[3] <= last_due_open
                ]
                if not trade_buckets:
                    continue
                start_open = min(trade_buckets)

            for open_time_ms in range(start_open, last_due_open + 1, SECOND_MS):
                key = (*stream_key, open_time_ms)
                state = self._open.pop(key, None)
                has_gap = self._has_gap(stream_key, open_time_ms)
                if state is None:
                    if has_gap:
                        candle = self._incomplete_candle(
                            stream_key,
                            open_time_ms,
                            now_ms,
                        )
                        finalized.append(candle)
                        self._last_finalized_open[stream_key] = open_time_ms
                        continue
                    previous_close = self._last_close.get(stream_key)
                    if previous_close is None:
                        continue
                    state = _CandleState.empty(
                        stream_key,
                        open_time_ms,
                        previous_close,
                    )

                candle = state.finalize(
                    now_ms,
                    status="incomplete" if has_gap else None,
                )
                finalized.append(candle)
                self._remember_finalized(key, state)
                self._last_finalized_open[stream_key] = open_time_ms
                if candle.close is not None and candle.status != "incomplete":
                    self._last_close[stream_key] = candle.close

        return finalized

    def mark_gap(
        self,
        stream_key: StreamKey,
        start_ms: int,
        end_ms: int,
    ) -> None:
        if end_ms <= start_ms:
            return
        self._gaps.setdefault(stream_key, []).append((start_ms, end_ms))
        self._gaps[stream_key] = self._gaps[stream_key][-100:]
        self._last_close.pop(stream_key, None)

    def provisional(self) -> List[Candle]:
        return [
            state.finalize(state.open_time_ms + SECOND_MS, status="provisional")
            for state in self._open.values()
        ]

    def _next_open_time(self, stream_key: StreamKey) -> Optional[int]:
        previous = self._last_finalized_open.get(stream_key)
        return None if previous is None else previous + SECOND_MS

    def _remember_finalized(
        self,
        key: CandleKey,
        state: _CandleState,
    ) -> None:
        self._finalized[key] = state
        self._finalized.move_to_end(key)
        while len(self._finalized) > self.finalized_cache_size:
            self._finalized.popitem(last=False)

    def _has_gap(self, stream_key: StreamKey, open_time_ms: int) -> bool:
        close_time_ms = open_time_ms + SECOND_MS
        return any(
            gap_start < close_time_ms and gap_end > open_time_ms
            for gap_start, gap_end in self._gaps.get(stream_key, ())
        )

    @staticmethod
    def _incomplete_candle(
        stream_key: StreamKey,
        open_time_ms: int,
        finalized_at_ms: int,
    ) -> Candle:
        exchange, market_type, instrument_id = stream_key
        return Candle(
            exchange=exchange,
            market_type=market_type,
            instrument_id=instrument_id,
            timeframe="1s",
            open_time_ms=open_time_ms,
            close_time_ms=open_time_ms + SECOND_MS,
            open=None,
            high=None,
            low=None,
            close=None,
            base_volume=Decimal("0"),
            quote_volume=Decimal("0"),
            trade_count=0,
            status="incomplete",
            revision=1,
            first_trade_id=None,
            last_trade_id=None,
            finalized_at_ms=finalized_at_ms,
        )
