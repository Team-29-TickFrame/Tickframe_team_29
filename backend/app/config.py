from dataclasses import dataclass
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "markets.yaml"


@dataclass(frozen=True)
class ExchangeConfig:
    name: str
    websocket_urls: Tuple[str, ...]

    @property
    def websocket_url(self) -> str:
        return self.websocket_urls[0]


@dataclass(frozen=True)
class InstrumentConfig:
    instrument_id: str
    name: str
    base: str
    quote: str
    symbols: Dict[str, str]

    def symbol_for(self, exchange: str) -> str:
        return self.symbols[exchange]


@dataclass(frozen=True)
class AppConfig:
    config_version: str
    market_type: str
    base_timeframe: str
    allowed_lateness_ms: int
    raw_trade_retention_hours: int
    exchanges: Dict[str, ExchangeConfig]
    instruments: List[InstrumentConfig]

    def subscriptions_for(self, exchange: str) -> Iterable[InstrumentConfig]:
        return (
            instrument
            for instrument in self.instruments
            if exchange in instrument.symbols
        )

    def instrument_by_id(self, instrument_id: str) -> Optional[InstrumentConfig]:
        for instrument in self.instruments:
            if instrument.instrument_id == instrument_id:
                return instrument
        return None

    def supports_instrument(self, exchange: str, instrument_id: str) -> bool:
        instrument = self.instrument_by_id(instrument_id)
        if instrument is None:
            return False
        return exchange in instrument.symbols

    def instrument_by_exchange_symbol(
        self,
        exchange: str,
        exchange_symbol: str,
    ) -> InstrumentConfig:
        for instrument in self.instruments:
            if instrument.symbols.get(exchange) == exchange_symbol:
                return instrument
        raise KeyError(f"Unknown {exchange} symbol: {exchange_symbol}")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {
        "config_version",
        "market_type",
        "base_timeframe",
        "allowed_lateness_ms",
        "raw_trade_retention_hours",
        "exchanges",
        "instruments",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"Missing configuration fields: {sorted(missing)}")

    exchanges = {
        name: ExchangeConfig(
            name=name,
            websocket_urls=websocket_urls_for(name, values),
        )
        for name, values in payload["exchanges"].items()
    }
    instruments = [
        InstrumentConfig(
            instrument_id=values["id"],
            name=values["name"],
            base=values["base"],
            quote=values["quote"],
            symbols=dict(values["symbols"]),
        )
        for values in payload["instruments"]
    ]

    instrument_ids = [instrument.instrument_id for instrument in instruments]
    if len(instrument_ids) != len(set(instrument_ids)):
        raise ValueError("Instrument IDs must be unique")

    for instrument in instruments:
        unknown_exchanges = set(instrument.symbols).difference(exchanges)
        if unknown_exchanges:
            raise ValueError(
                f"{instrument.instrument_id} uses unknown exchanges: "
                f"{sorted(unknown_exchanges)}"
            )

    return AppConfig(
        config_version=str(payload["config_version"]),
        market_type=str(payload["market_type"]),
        base_timeframe=str(payload["base_timeframe"]),
        allowed_lateness_ms=int(payload["allowed_lateness_ms"]),
        raw_trade_retention_hours=int(payload["raw_trade_retention_hours"]),
        exchanges=exchanges,
        instruments=instruments,
    )


def websocket_urls_for(
    exchange_name: str, values: Dict[str, object]
) -> Tuple[str, ...]:
    env_name = f"TICKFRAME_{exchange_name.upper()}_WS_URLS"
    configured = os.getenv(env_name)
    if configured:
        urls = parse_url_list(configured.split(","))
    elif "websocket_urls" in values:
        raw_urls = values["websocket_urls"]
        if not isinstance(raw_urls, list):
            raise ValueError(f"{exchange_name}.websocket_urls must be a list")
        urls = parse_url_list(raw_urls)
    elif "websocket_url" in values:
        urls = parse_url_list([values["websocket_url"]])
    else:
        raise ValueError(f"{exchange_name} must define websocket_urls")

    if not urls:
        raise ValueError(f"{exchange_name} must define at least one WebSocket URL")
    return tuple(urls)


def parse_url_list(raw_urls: Iterable[object]) -> List[str]:
    urls: List[str] = []
    seen = set()
    for raw_url in raw_urls:
        url = str(raw_url).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls
