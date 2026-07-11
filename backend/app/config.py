from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

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
    _instruments_by_id: Dict[str, InstrumentConfig] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _instruments_by_symbol: Dict[Tuple[str, str], InstrumentConfig] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_instruments_by_id",
            {instrument.instrument_id: instrument for instrument in self.instruments},
        )
        object.__setattr__(
            self,
            "_instruments_by_symbol",
            {
                (exchange, symbol): instrument
                for instrument in self.instruments
                for exchange, symbol in instrument.symbols.items()
            },
        )

    def subscriptions_for(self, exchange: str) -> Iterable[InstrumentConfig]:
        return (
            instrument
            for instrument in self.instruments
            if exchange in instrument.symbols
        )

    def instrument_by_id(self, instrument_id: str) -> Optional[InstrumentConfig]:
        return self._instruments_by_id.get(instrument_id)

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
        try:
            return self._instruments_by_symbol[(exchange, exchange_symbol)]
        except KeyError as error:
            raise KeyError(f"Unknown {exchange} symbol: {exchange_symbol}") from error


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Market configuration must be a YAML object")
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

    raw_exchanges = payload["exchanges"]
    if not isinstance(raw_exchanges, dict) or not raw_exchanges:
        raise ValueError("exchanges must be a non-empty object")
    exchanges: Dict[str, ExchangeConfig] = {}
    for raw_name, values in raw_exchanges.items():
        name = str(raw_name).strip()
        if not name or not isinstance(values, dict):
            raise ValueError("Each exchange must have a name and configuration")
        exchanges[name] = ExchangeConfig(
            name=name,
            websocket_urls=websocket_urls_for(name, values),
        )

    raw_instruments = payload["instruments"]
    if not isinstance(raw_instruments, list) or not raw_instruments:
        raise ValueError("instruments must be a non-empty list")
    instruments: List[InstrumentConfig] = []
    for index, values in enumerate(raw_instruments):
        if not isinstance(values, dict):
            raise ValueError(f"Instrument at index {index} must be an object")
        try:
            symbols = values["symbols"]
            if not isinstance(symbols, dict) or not symbols:
                raise ValueError("symbols must be a non-empty object")
            instrument = InstrumentConfig(
                instrument_id=str(values["id"]).strip(),
                name=str(values["name"]).strip(),
                base=str(values["base"]).strip(),
                quote=str(values["quote"]).strip(),
                symbols={
                    str(exchange).strip(): str(symbol).strip()
                    for exchange, symbol in symbols.items()
                },
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid instrument at index {index}: {error}") from error
        if not all(
            (
                instrument.instrument_id,
                instrument.name,
                instrument.base,
                instrument.quote,
                *instrument.symbols.keys(),
                *instrument.symbols.values(),
            )
        ):
            raise ValueError(f"Instrument at index {index} contains an empty value")
        instruments.append(instrument)

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

    exchange_symbols: Dict[Tuple[str, str], str] = {}
    for instrument in instruments:
        for exchange, symbol in instrument.symbols.items():
            key = (exchange, symbol)
            existing = exchange_symbols.get(key)
            if existing is not None:
                raise ValueError(
                    f"Duplicate {exchange} symbol {symbol}: "
                    f"{existing} and {instrument.instrument_id}"
                )
            exchange_symbols[key] = instrument.instrument_id

    allowed_lateness_ms = int(payload["allowed_lateness_ms"])
    raw_trade_retention_hours = int(payload["raw_trade_retention_hours"])
    if allowed_lateness_ms < 0:
        raise ValueError("allowed_lateness_ms must be non-negative")
    if raw_trade_retention_hours <= 0:
        raise ValueError("raw_trade_retention_hours must be positive")
    base_timeframe = str(payload["base_timeframe"]).strip()
    if base_timeframe != "1s":
        raise ValueError("base_timeframe must be 1s")

    return AppConfig(
        config_version=str(payload["config_version"]),
        market_type=str(payload["market_type"]),
        base_timeframe=base_timeframe,
        allowed_lateness_ms=allowed_lateness_ms,
        raw_trade_retention_hours=raw_trade_retention_hours,
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
        parsed = urlparse(url)
        if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
            raise ValueError(f"Invalid WebSocket URL: {url}")
        seen.add(url)
        urls.append(url)
    return urls
