import os
import unittest
from typing import Optional

from backend.app.config import load_config


class ConfigTests(unittest.TestCase):
    def test_exchange_support_matrix_is_explicit(self) -> None:
        config = load_config()

        self.assertTrue(config.supports_instrument("binance", "TON-USDT"))
        self.assertTrue(config.supports_instrument("bybit", "TON-USDT"))
        self.assertTrue(config.supports_instrument("bybit", "BTC-USDT"))

    def test_default_websocket_endpoint_fallbacks_are_configured(self) -> None:
        with temporary_env(
            TICKFRAME_BINANCE_WS_URLS=None,
            TICKFRAME_BYBIT_WS_URLS=None,
        ):
            config = load_config()

        self.assertGreaterEqual(len(config.exchanges["binance"].websocket_urls), 2)
        self.assertGreaterEqual(len(config.exchanges["bybit"].websocket_urls), 3)
        self.assertEqual(
            config.exchanges["binance"].websocket_url,
            config.exchanges["binance"].websocket_urls[0],
        )

    def test_websocket_endpoints_can_be_overridden_from_env(self) -> None:
        with temporary_env(
            TICKFRAME_BYBIT_WS_URLS=(
                "wss://example-one.test/ws, "
                "wss://example-two.test/ws, "
                "wss://example-one.test/ws"
            )
        ):
            config = load_config()

        self.assertEqual(
            config.exchanges["bybit"].websocket_urls,
            ("wss://example-one.test/ws", "wss://example-two.test/ws"),
        )


class temporary_env:
    def __init__(self, **values: Optional[str]) -> None:
        self.values = values
        self.previous: dict[str, Optional[str]] = {}

    def __enter__(self) -> None:
        for name, value in self.values.items():
            self.previous[name] = os.environ.get(name)
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def __exit__(self, *args: object) -> None:
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
