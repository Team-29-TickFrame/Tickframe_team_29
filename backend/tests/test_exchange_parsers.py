import unittest
from decimal import Decimal

from backend.app.config import load_config
from backend.app.exchanges.binance import parse_binance_message
from backend.app.exchanges.bybit import BybitCollector, parse_bybit_message


class ExchangeParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()

    def test_binance_trade_is_normalized(self) -> None:
        trades = parse_binance_message(
            {
                "stream": "btcusdt@trade",
                "data": {
                    "e": "trade",
                    "E": 1_700_000_000_010,
                    "s": "BTCUSDT",
                    "t": 12345,
                    "p": "64000.125",
                    "q": "0.002",
                    "T": 1_700_000_000_000,
                    "m": False,
                },
            },
            self.config,
            received_timestamp_ms=1_700_000_000_020,
        )

        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.exchange, "binance")
        self.assertEqual(trade.instrument_id, "BTC-USDT")
        self.assertEqual(trade.trade_id, "12345")
        self.assertEqual(trade.price, Decimal("64000.125"))
        self.assertEqual(trade.base_quantity, Decimal("0.002"))
        self.assertEqual(trade.side, "buy")
        self.assertEqual(trade.latency_ms, 20)

    def test_bybit_trade_batch_is_normalized(self) -> None:
        trades = parse_bybit_message(
            {
                "topic": "publicTrade.PENGUUSDT",
                "type": "snapshot",
                "ts": 1_700_000_000_010,
                "data": [
                    {
                        "T": 1_700_000_000_000,
                        "s": "PENGUUSDT",
                        "S": "Sell",
                        "v": "1000",
                        "p": "0.00718",
                        "i": "trade-1",
                        "seq": 42,
                    }
                ],
            },
            self.config,
            received_timestamp_ms=1_700_000_000_025,
        )

        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.exchange, "bybit")
        self.assertEqual(trade.instrument_id, "PENGU-USDT")
        self.assertEqual(trade.price, Decimal("0.00718"))
        self.assertEqual(trade.quote_quantity, Decimal("7.18000"))
        self.assertEqual(trade.side, "sell")
        self.assertEqual(trade.sequence, 42)

    def test_bybit_gram_trade_is_normalized(self) -> None:
        trades = parse_bybit_message(
            {
                "topic": "publicTrade.GRAMUSDT",
                "type": "snapshot",
                "ts": 1_700_000_000_010,
                "data": [
                    {
                        "T": 1_700_000_000_000,
                        "s": "GRAMUSDT",
                        "S": "Buy",
                        "v": "12.5",
                        "p": "2.400",
                        "i": "gram-trade-1",
                        "seq": 84,
                    }
                ],
            },
            self.config,
            received_timestamp_ms=1_700_000_000_025,
        )

        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.exchange, "bybit")
        self.assertEqual(trade.instrument_id, "GRAM-USDT")
        self.assertEqual(trade.exchange_symbol, "GRAMUSDT")
        self.assertEqual(trade.price, Decimal("2.400"))
        self.assertEqual(trade.base_quantity, Decimal("12.5"))
        self.assertEqual(trade.side, "buy")


async def async_noop(*args: object) -> None:
    return None


class FakeWebsocket:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, payload: str) -> None:
        self.sent.append(payload)


class BybitCollectorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.config = load_config()
        self.collector = BybitCollector(
            self.config,
            self.config.subscriptions_for("bybit"),
            async_noop,
            async_noop,
        )

    async def test_bybit_subscribes_one_topic_per_request(self) -> None:
        websocket = FakeWebsocket()

        await self.collector._subscribe(websocket)

        self.assertEqual(len(websocket.sent), 10)
        self.assertTrue(
            all('"args": ["publicTrade.' in payload for payload in websocket.sent)
        )
        self.assertIn(
            "publicTrade.GRAMUSDT",
            self.collector._pending_subscriptions.values(),
        )

    async def test_bybit_rejected_topic_is_tracked(self) -> None:
        websocket = FakeWebsocket()
        await self.collector._subscribe(websocket)

        self.collector._handle_control_message(
            {
                "success": False,
                "ret_msg": "Invalid symbol :[publicTrade.GRAMUSDT]",
                "req_id": "tickframe-bybit-6",
                "op": "subscribe",
            }
        )

        self.assertEqual(
            self.collector.rejected_topics["publicTrade.GRAMUSDT"],
            "Invalid symbol :[publicTrade.GRAMUSDT]",
        )
        self.assertFalse(self.collector.is_instrument_active("GRAM-USDT"))


if __name__ == "__main__":
    unittest.main()
