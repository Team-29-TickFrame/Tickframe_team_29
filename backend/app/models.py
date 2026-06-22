from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class Trade:
    exchange: str
    market_type: str
    instrument_id: str
    exchange_symbol: str
    trade_id: str
    exchange_timestamp_ms: int
    received_timestamp_ms: int
    price: Decimal
    base_quantity: Decimal
    side: str
    sequence: Optional[int] = None

    @property
    def quote_quantity(self) -> Decimal:
        return self.price * self.base_quantity

    @property
    def latency_ms(self) -> int:
        return max(0, self.received_timestamp_ms - self.exchange_timestamp_ms)

    @property
    def stream_key(self) -> Tuple[str, str, str]:
        return (self.exchange, self.market_type, self.instrument_id)

    def to_api(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "marketType": self.market_type,
            "instrumentId": self.instrument_id,
            "exchangeSymbol": self.exchange_symbol,
            "tradeId": self.trade_id,
            "exchangeTimestamp": self.exchange_timestamp_ms,
            "receivedTimestamp": self.received_timestamp_ms,
            "latencyMs": self.latency_ms,
            "price": str(self.price),
            "baseQuantity": str(self.base_quantity),
            "quoteQuantity": str(self.quote_quantity),
            "side": self.side,
        }


@dataclass(frozen=True)
class Candle:
    exchange: str
    market_type: str
    instrument_id: str
    timeframe: str
    open_time_ms: int
    close_time_ms: int
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    base_volume: Decimal
    quote_volume: Decimal
    trade_count: int
    status: str
    revision: int
    first_trade_id: Optional[str]
    last_trade_id: Optional[str]
    finalized_at_ms: int
    current: bool = True

    @property
    def stream_key(self) -> Tuple[str, str, str]:
        return (self.exchange, self.market_type, self.instrument_id)

    def superseded(self) -> "Candle":
        return replace(self, current=False)

    def to_api(self) -> Dict[str, Any]:
        def decimal_value(value: Optional[Decimal]) -> Optional[str]:
            return None if value is None else str(value)

        return {
            "exchange": self.exchange,
            "marketType": self.market_type,
            "instrumentId": self.instrument_id,
            "timeframe": self.timeframe,
            "openTime": self.open_time_ms,
            "closeTime": self.close_time_ms,
            "open": decimal_value(self.open),
            "high": decimal_value(self.high),
            "low": decimal_value(self.low),
            "close": decimal_value(self.close),
            "baseVolume": str(self.base_volume),
            "quoteVolume": str(self.quote_volume),
            "tradeCount": self.trade_count,
            "status": self.status,
            "revision": self.revision,
            "firstTradeId": self.first_trade_id,
            "lastTradeId": self.last_trade_id,
            "finalizedAt": self.finalized_at_ms,
        }
