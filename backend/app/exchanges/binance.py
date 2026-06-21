import json
from decimal import Decimal
from typing import Dict, Iterable, List
from urllib.parse import urlencode

import websockets

from ..config import AppConfig, InstrumentConfig
from ..models import Trade
from .base import ExchangeCollector, StateHandler, TradeHandler, unix_ms


def parse_binance_message(
    message: Dict[str, object],
    config: AppConfig,
    received_timestamp_ms: int,
) -> List[Trade]:
    payload = message.get("data", message)
    if not isinstance(payload, dict) or payload.get("e") != "trade":
        return []

    exchange_symbol = str(payload["s"])
    instrument = config.instrument_by_exchange_symbol("binance", exchange_symbol)
    return [
        Trade(
            exchange="binance",
            market_type=config.market_type,
            instrument_id=instrument.instrument_id,
            exchange_symbol=exchange_symbol,
            trade_id=str(payload["t"]),
            exchange_timestamp_ms=int(payload["T"]),
            received_timestamp_ms=received_timestamp_ms,
            price=Decimal(str(payload["p"])),
            base_quantity=Decimal(str(payload["q"])),
            side="sell" if bool(payload["m"]) else "buy",
        )
    ]


class BinanceCollector(ExchangeCollector):
    def __init__(
        self,
        config: AppConfig,
        instruments: Iterable[InstrumentConfig],
        on_trade: TradeHandler,
        on_state_change: StateHandler,
    ) -> None:
        super().__init__("binance", on_trade, on_state_change)
        self.config = config
        self.instruments = list(instruments)
        self.websocket_urls = config.exchanges["binance"].websocket_urls
        self._websocket_url_index = 0

    async def connect_once(self) -> None:
        streams = "/".join(
            f"{instrument.symbol_for('binance').lower()}@trade"
            for instrument in self.instruments
        )
        websocket_url = self._current_websocket_url()
        self.active_endpoint = websocket_url
        url = f"{websocket_url}?{urlencode({'streams': streams})}"

        try:
            async with websockets.connect(
                url,
                ping_interval=None,
                close_timeout=5,
                max_queue=4096,
            ) as websocket:
                await self.set_connected(True)
                self.last_error = None
                try:
                    async for raw_message in websocket:
                        received_at = unix_ms()
                        self.last_message_at = received_at
                        message = json.loads(raw_message)
                        for trade in parse_binance_message(
                            message,
                            self.config,
                            received_at,
                        ):
                            await self.on_trade(trade)
                finally:
                    await self.set_connected(False)
        except Exception:
            self.endpoint_failures += 1
            self._rotate_websocket_url()
            raise
        else:
            self._rotate_websocket_url()

    def _current_websocket_url(self) -> str:
        return self.websocket_urls[self._websocket_url_index % len(self.websocket_urls)]

    def _rotate_websocket_url(self) -> None:
        self._websocket_url_index = (
            self._websocket_url_index + 1
        ) % len(self.websocket_urls)
