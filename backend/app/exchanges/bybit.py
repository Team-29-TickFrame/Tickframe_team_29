import asyncio
import json
from decimal import Decimal
from typing import Dict, Iterable, List, Set

import websockets

from ..config import AppConfig, InstrumentConfig
from ..models import Trade
from .base import ExchangeCollector, StateHandler, TradeHandler, unix_ms


def parse_bybit_message(
    message: Dict[str, object],
    config: AppConfig,
    received_timestamp_ms: int,
) -> List[Trade]:
    topic = str(message.get("topic", ""))
    payload = message.get("data")
    if not topic.startswith("publicTrade.") or not isinstance(payload, list):
        return []

    trades: List[Trade] = []
    for values in payload:
        if not isinstance(values, dict):
            continue
        exchange_symbol = str(values["s"])
        instrument = config.instrument_by_exchange_symbol("bybit", exchange_symbol)
        trades.append(
            Trade(
                exchange="bybit",
                market_type=config.market_type,
                instrument_id=instrument.instrument_id,
                exchange_symbol=exchange_symbol,
                trade_id=str(values["i"]),
                exchange_timestamp_ms=int(values["T"]),
                received_timestamp_ms=received_timestamp_ms,
                price=Decimal(str(values["p"])),
                base_quantity=Decimal(str(values["v"])),
                side=str(values["S"]).lower(),
                sequence=int(values["seq"]) if values.get("seq") is not None else None,
            )
        )
    return trades


class BybitCollector(ExchangeCollector):
    def __init__(
        self,
        config: AppConfig,
        instruments: Iterable[InstrumentConfig],
        on_trade: TradeHandler,
        on_state_change: StateHandler,
    ) -> None:
        super().__init__("bybit", on_trade, on_state_change)
        self.config = config
        self.instruments = list(instruments)
        self.websocket_urls = config.exchanges["bybit"].websocket_urls
        self._websocket_url_index = 0
        self._topic_by_instrument_id = {
            instrument.instrument_id: f"publicTrade.{instrument.symbol_for('bybit')}"
            for instrument in self.instruments
        }
        self._pending_subscriptions: Dict[str, str] = {}
        self.accepted_topics: Set[str] = set()
        self.rejected_topics: Dict[str, str] = {}

    async def connect_once(self) -> None:
        websocket_url = self._current_websocket_url()
        self.active_endpoint = websocket_url
        try:
            async with websockets.connect(
                websocket_url,
                ping_interval=None,
                close_timeout=5,
                max_queue=4096,
            ) as websocket:
                await self.set_connected(True)
                self.last_error = None
                await self._subscribe(websocket)
                heartbeat = asyncio.create_task(self._heartbeat(websocket))
                try:
                    async for raw_message in websocket:
                        received_at = unix_ms()
                        message = json.loads(raw_message)
                        self._handle_control_message(message)
                        trades = parse_bybit_message(
                            message,
                            self.config,
                            received_at,
                        )
                        if trades:
                            self.last_message_at = received_at
                        for trade in trades:
                            await self.on_trade(trade)
                finally:
                    await self.set_connected(False)
                    heartbeat.cancel()
                    try:
                        await heartbeat
                    except asyncio.CancelledError:
                        pass
        except Exception:
            self.endpoint_failures += 1
            self._rotate_websocket_url()
            raise
        else:
            self._rotate_websocket_url()

    async def _subscribe(self, websocket: object) -> None:
        self._pending_subscriptions = {}
        self.accepted_topics = set()
        self.rejected_topics = {}
        topics = list(self._topic_by_instrument_id.values())
        for request_id, topic in enumerate(topics, start=1):
            req_id = f"tickframe-bybit-{request_id}"
            self._pending_subscriptions[req_id] = topic
            await websocket.send(
                json.dumps(
                    {
                        "req_id": req_id,
                        "op": "subscribe",
                        "args": [topic],
                    }
                )
            )

    def _handle_control_message(self, message: Dict[str, object]) -> None:
        if message.get("op") != "subscribe":
            return
        req_id = str(message.get("req_id", ""))
        topic = self._pending_subscriptions.pop(req_id, None)
        if topic is None:
            return

        if message.get("success") is True:
            self.accepted_topics.add(topic)
            self.rejected_topics.pop(topic, None)
            return

        if message.get("success") is False:
            self.accepted_topics.discard(topic)
            self.rejected_topics[topic] = str(
                message.get("ret_msg") or "subscription rejected"
            )

    async def _heartbeat(self, websocket: object) -> None:
        while True:
            await asyncio.sleep(20)
            await websocket.send(
                json.dumps({"req_id": "tickframe-heartbeat", "op": "ping"})
            )

    def _current_websocket_url(self) -> str:
        return self.websocket_urls[self._websocket_url_index % len(self.websocket_urls)]

    def _rotate_websocket_url(self) -> None:
        self._websocket_url_index = (self._websocket_url_index + 1) % len(
            self.websocket_urls
        )

    def is_instrument_active(self, instrument_id: str) -> bool:
        topic = self._topic_by_instrument_id.get(instrument_id)
        return self.connected and topic in self.accepted_topics

    def health(self) -> Dict[str, object]:
        payload = super().health()
        payload.update(
            {
                "acceptedTopics": sorted(self.accepted_topics),
                "pendingTopics": sorted(self._pending_subscriptions.values()),
                "rejectedTopics": dict(sorted(self.rejected_topics.items())),
            }
        )
        return payload
