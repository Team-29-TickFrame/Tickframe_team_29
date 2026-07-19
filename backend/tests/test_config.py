import os
from pathlib import Path
import tempfile
import unittest
from typing import Optional

from backend.app.config import DEFAULT_CONFIG_PATH, load_config


class ConfigTests(unittest.TestCase):
    def test_exchange_support_matrix_is_explicit(self) -> None:
        config = load_config()

        self.assertFalse(config.supports_instrument("binance", "GRAM-USDT"))
        self.assertTrue(config.supports_instrument("bybit", "GRAM-USDT"))
        self.assertTrue(config.supports_instrument("bybit", "BTC-USDT"))
        self.assertEqual(
            config.instrument_by_exchange_symbol("bybit", "GRAMUSDT").instrument_id,
            "GRAM-USDT",
        )

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

    def test_invalid_websocket_override_is_rejected_at_startup(self) -> None:
        with temporary_env(TICKFRAME_BYBIT_WS_URLS="https://example.test/ws"):
            with self.assertRaisesRegex(ValueError, "Invalid WebSocket URL"):
                load_config()

    def test_runtime_market_settings_can_be_overridden_from_env(self) -> None:
        with temporary_env(
            TICKFRAME_ENABLED_INSTRUMENTS="btc-usdt, gram-usdt",
            TICKFRAME_ALLOWED_LATENESS_MS="3500",
            TICKFRAME_RAW_TRADE_RETENTION_HOURS="48",
        ):
            config = load_config()

        self.assertEqual(
            [instrument.instrument_id for instrument in config.instruments],
            ["BTC-USDT", "GRAM-USDT"],
        )
        self.assertEqual(config.allowed_lateness_ms, 3500)
        self.assertEqual(config.raw_trade_retention_hours, 48)

    def test_unknown_enabled_instrument_is_rejected(self) -> None:
        with temporary_env(TICKFRAME_ENABLED_INSTRUMENTS="UNKNOWN-USDT"):
            with self.assertRaisesRegex(ValueError, "unknown IDs"):
                load_config()

    def test_invalid_numeric_override_is_rejected(self) -> None:
        with temporary_env(TICKFRAME_ALLOWED_LATENESS_MS="soon"):
            with self.assertRaisesRegex(ValueError, "must be an integer"):
                load_config()

    def test_market_config_path_can_be_overridden_from_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "markets.yaml"
            config_path.write_text(
                DEFAULT_CONFIG_PATH.read_text(encoding="utf-8").replace(
                    'config_version: "1.0.1"',
                    'config_version: "env-test"',
                ),
                encoding="utf-8",
            )
            with temporary_env(TICKFRAME_MARKETS_CONFIG_PATH=str(config_path)):
                config = load_config()

        self.assertEqual(config.config_version, "env-test")


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
