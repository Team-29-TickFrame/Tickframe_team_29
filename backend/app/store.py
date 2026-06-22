import asyncio
from collections import defaultdict, deque
from copy import deepcopy
from typing import Any, Deque, Dict, List, Optional, Tuple

from .config import AppConfig
from .models import Candle, Trade


MarketKey = Tuple[str, str]


class LiveStore:
    def __init__(self, config: AppConfig, candle_limit: int = 3600) -> None:
        self.config = config
        self.candle_limit = candle_limit
        self._lock = asyncio.Lock()
        self._revision = 0
        self._latest: Dict[MarketKey, Dict[str, Any]] = {}
        self._candles: Dict[MarketKey, Deque[Candle]] = defaultdict(
            lambda: deque(maxlen=self.candle_limit)
        )

        for exchange in config.exchanges:
            for instrument in config.subscriptions_for(exchange):
                self._latest[(exchange, instrument.instrument_id)] = {
                    "exchange": exchange,
                    "marketType": config.market_type,
                    "instrumentId": instrument.instrument_id,
                    "name": instrument.name,
                    "base": instrument.base,
                    "quote": instrument.quote,
                    "exchangeSymbol": instrument.symbol_for(exchange),
                    "price": None,
                    "lastTradeSize": None,
                    "lastTradeSide": None,
                    "exchangeTimestamp": None,
                    "receivedTimestamp": None,
                    "latencyMs": None,
                }

    @property
    def revision(self) -> int:
        return self._revision

    async def apply_trade(self, trade: Trade) -> None:
        async with self._lock:
            market = self._latest[(trade.exchange, trade.instrument_id)]
            market.update(
                {
                    "price": str(trade.price),
                    "lastTradeSize": str(trade.base_quantity),
                    "lastTradeSide": trade.side,
                    "exchangeTimestamp": trade.exchange_timestamp_ms,
                    "receivedTimestamp": trade.received_timestamp_ms,
                    "latencyMs": trade.latency_ms,
                }
            )
            self._revision += 1

    async def apply_candle(self, candle: Candle) -> None:
        key = (candle.exchange, candle.instrument_id)
        async with self._lock:
            values = self._candles[key]
            if values and values[-1].open_time_ms == candle.open_time_ms:
                values[-1] = candle
            else:
                values.append(candle)
            self._revision += 1

    async def market_snapshot(
        self,
        now_ms: int,
        exchange: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self._lock:
            markets = deepcopy(list(self._latest.values()))
            revision = self._revision

        if exchange is not None:
            markets = [market for market in markets if market["exchange"] == exchange]

        for market in markets:
            received_at = market["receivedTimestamp"]
            age_ms = now_ms - received_at if received_at else None
            market["ageMs"] = age_ms
            if received_at is None:
                market["status"] = "waiting"
            elif age_ms > 10_000:
                market["status"] = "stale"
            else:
                market["status"] = "live"

        return {
            "configVersion": self.config.config_version,
            "revision": revision,
            "generatedAt": now_ms,
            "markets": markets,
        }

    async def candle_snapshot(
        self,
        exchange: str,
        instrument_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        key = (exchange, instrument_id)
        async with self._lock:
            candles = list(self._candles.get(key, ()))
        return [candle.to_api() for candle in candles[-limit:]]
