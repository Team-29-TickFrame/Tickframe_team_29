from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence

import asyncpg

from backend.app.config import InstrumentConfig, load_config


INTERVAL_MS = {
    "1s": 1_000,
    "1m": 60_000,
}

BINANCE_BASE_URLS = (
    "https://data-api.binance.vision/api/v3/klines",
    "https://api.binance.com/api/v3/klines",
)

DEFAULT_BYBIT_BASE_URLS = (
    "https://api.bybit.kz/v5/market/kline",
    "https://api.bybit.com/v5/market/kline",
    "https://api.bytick.com/v5/market/kline",
    "https://api.bybitgeorgia.ge/v5/market/kline",
    "https://api.bybit.ae/v5/market/kline",
    "https://api.bybit.tr/v5/market/kline",
)

DEFAULT_DAYS = 30
DEFAULT_LIMIT = 1000


@dataclass(frozen=True)
class HistoricalCandle:
    exchange: str
    market_type: str
    instrument_id: str
    timeframe: str
    source: str
    source_symbol: str
    open_time_ms: int
    close_time_ms: int
    open: str
    high: str
    low: str
    close: str
    base_volume: str
    quote_volume: str
    trade_count: int
    status: str
    revision: int
    finalized_at_ms: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parallel backfill public exchange OHLCV into historical_candles."
    )
    parser.add_argument("--days", type=float, default=DEFAULT_DAYS)
    parser.add_argument("--timeframe", choices=sorted(INTERVAL_MS), default="1m")
    parser.add_argument(
        "--exchange", choices=("all", "binance", "bybit"), default="all"
    )
    parser.add_argument("--instrument", default="all")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument("--request-sleep", type=float, default=0.03)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--binance-concurrency", type=int, default=5)
    parser.add_argument("--bybit-concurrency", type=int, default=5)
    parser.add_argument("--until-ms", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Exit successfully even if one or more markets fail.",
    )
    parser.add_argument(
        "--database-url",
        default=normalize_database_url(
            os.getenv("DATABASE_URL") or os.getenv("TICKFRAME_DATABASE_URL")
        ),
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    config = load_config()

    interval_ms = INTERVAL_MS[args.timeframe]
    end_ms = align_closed_end_ms(args.until_ms, interval_ms)
    start_ms = end_ms - int(args.days * 24 * 60 * 60 * 1000)

    exchanges = list(config.exchanges) if args.exchange == "all" else [args.exchange]
    instruments = select_instruments(config.instruments, args.instrument)

    if not args.dry_run and not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")

    pool: Optional[asyncpg.Pool] = None
    if not args.dry_run:
        pool = await asyncpg.create_pool(
            dsn=args.database_url,
            min_size=1,
            max_size=max(3, args.binance_concurrency + args.bybit_concurrency),
        )

    semaphores = {
        "binance": asyncio.Semaphore(args.binance_concurrency),
        "bybit": asyncio.Semaphore(args.bybit_concurrency),
    }
    failures: List[str] = []

    async def run_one(exchange: str, instrument: InstrumentConfig) -> int:
        if exchange not in instrument.symbols:
            return 0
        if not supports_rest_timeframe(exchange, args.timeframe):
            print(
                "warning "
                f"exchange={exchange} instrument={instrument.instrument_id} "
                f"timeframe={args.timeframe} "
                "reason=unsupported_rest_timeframe"
            )
            return 0

        async with semaphores[exchange]:
            try:
                return await backfill_market(
                    pool=pool,
                    exchange=exchange,
                    market_type=config.market_type,
                    instrument=instrument,
                    timeframe=args.timeframe,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    limit=args.limit,
                    batch_size=args.batch_size,
                    request_sleep=args.request_sleep,
                    max_retries=args.max_retries,
                    dry_run=args.dry_run,
                )
            except Exception as error:
                failure = (
                    f"exchange={exchange} "
                    f"instrument={instrument.instrument_id} "
                    f"reason={repr(error)}"
                )
                failures.append(failure)
                print(f"error {failure}")
                return 0

    tasks = [
        run_one(exchange, instrument)
        for exchange in exchanges
        for instrument in instruments
    ]

    try:
        results = await asyncio.gather(*tasks)
    finally:
        if pool is not None:
            await pool.close()

    total_candles = sum(results)
    print(f"done total_candles={total_candles} failed_markets={len(failures)}")
    if failures and not args.allow_failures:
        raise SystemExit(1)


async def backfill_market(
    *,
    pool: Optional[asyncpg.Pool],
    exchange: str,
    market_type: str,
    instrument: InstrumentConfig,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    batch_size: int,
    request_sleep: float,
    max_retries: int,
    dry_run: bool,
) -> int:
    symbol = instrument.symbol_for(exchange)
    cursor = start_ms
    interval_ms = INTERVAL_MS[timeframe]
    total = 0
    pending: List[HistoricalCandle] = []
    first_loaded_open_ms: Optional[int] = None
    last_loaded_open_ms: Optional[int] = None

    print(
        "market "
        f"exchange={exchange} instrument={instrument.instrument_id} "
        f"symbol={symbol} start_ms={start_ms} end_ms={end_ms}"
    )

    while cursor < end_ms:
        request_end_ms = min(cursor + limit * interval_ms, end_ms)

        candles = await fetch_candles(
            exchange=exchange,
            market_type=market_type,
            instrument_id=instrument.instrument_id,
            symbol=symbol,
            timeframe=timeframe,
            start_ms=cursor,
            end_ms=request_end_ms,
            limit=limit,
            max_retries=max_retries,
        )

        candles = [
            candle for candle in candles if cursor <= candle.open_time_ms < end_ms
        ]

        if not candles:
            cursor += limit * interval_ms
            await asyncio.sleep(request_sleep)
            continue

        batch_first_open_ms = min(candle.open_time_ms for candle in candles)
        batch_last_open_ms = max(candle.open_time_ms for candle in candles)
        if first_loaded_open_ms is None:
            first_loaded_open_ms = batch_first_open_ms
        last_loaded_open_ms = batch_last_open_ms

        pending.extend(candles)

        if len(pending) >= batch_size:
            total += await flush(pool, pending, dry_run=dry_run)
            pending = []

        cursor = batch_last_open_ms + interval_ms

        print(
            "progress "
            f"exchange={exchange} instrument={instrument.instrument_id} "
            f"loaded={total + len(pending)} cursor_ms={cursor}"
        )

        await asyncio.sleep(request_sleep)

    total += await flush(pool, pending, dry_run=dry_run)
    expected_last_open_ms = end_ms - interval_ms
    if first_loaded_open_ms is None or last_loaded_open_ms is None:
        print(
            "warning "
            f"exchange={exchange} instrument={instrument.instrument_id} "
            "reason=no_candles_returned "
            f"start_ms={start_ms} end_ms={end_ms}"
        )
    else:
        missing_head_bars = max(0, (first_loaded_open_ms - start_ms) // interval_ms)
        missing_tail_bars = max(
            0,
            (expected_last_open_ms - last_loaded_open_ms) // interval_ms,
        )
        if missing_head_bars or missing_tail_bars:
            print(
                "warning "
                f"exchange={exchange} instrument={instrument.instrument_id} "
                f"missing_head_bars={missing_head_bars} "
                f"missing_tail_bars={missing_tail_bars} "
                f"first_open_ms={first_loaded_open_ms} "
                f"last_open_ms={last_loaded_open_ms} "
                f"expected_last_open_ms={expected_last_open_ms}"
            )

    print(
        "market_done "
        f"exchange={exchange} instrument={instrument.instrument_id} "
        f"candles={total}"
    )

    return total


async def fetch_candles(
    *,
    exchange: str,
    market_type: str,
    instrument_id: str,
    symbol: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    max_retries: int,
) -> List[HistoricalCandle]:
    if exchange == "binance":
        return await fetch_binance(
            market_type=market_type,
            instrument_id=instrument_id,
            symbol=symbol,
            timeframe=timeframe,
            start_ms=start_ms,
            end_ms=end_ms,
            limit=limit,
            max_retries=max_retries,
        )

    if exchange == "bybit":
        return await fetch_bybit(
            market_type=market_type,
            instrument_id=instrument_id,
            symbol=symbol,
            timeframe=timeframe,
            start_ms=start_ms,
            end_ms=end_ms,
            limit=limit,
            max_retries=max_retries,
        )

    raise ValueError(f"Unsupported exchange: {exchange}")


async def fetch_binance(
    *,
    market_type: str,
    instrument_id: str,
    symbol: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    max_retries: int,
) -> List[HistoricalCandle]:
    query = {
        "symbol": symbol,
        "interval": timeframe,
        "startTime": str(start_ms),
        "endTime": str(end_ms - 1),
        "limit": str(limit),
    }

    last_error: Optional[Exception] = None

    for base_url in binance_base_urls():
        url = f"{base_url}?{urllib.parse.urlencode(query)}"
        try:
            payload = await http_json(url, max_retries=max_retries)
            return parse_binance_klines(
                payload,
                market_type=market_type,
                instrument_id=instrument_id,
                source_symbol=symbol,
                timeframe=timeframe,
            )
        except Exception as error:
            last_error = error

    assert last_error is not None
    raise last_error


async def fetch_bybit(
    *,
    market_type: str,
    instrument_id: str,
    symbol: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    max_retries: int,
) -> List[HistoricalCandle]:
    if timeframe == "1s":
        raise ValueError("Bybit Spot REST kline endpoint does not support 1s interval")
    query = {
        "category": "spot",
        "symbol": symbol,
        "interval": bybit_interval(timeframe),
        "start": str(start_ms),
        "end": str(end_ms - 1),
        "limit": str(limit),
    }

    last_error: Optional[Exception] = None

    for base_url in bybit_base_urls():
        url = f"{base_url}?{urllib.parse.urlencode(query)}"
        try:
            payload = await http_json(url, max_retries=max_retries)
            return parse_bybit_klines(
                payload,
                market_type=market_type,
                instrument_id=instrument_id,
                source_symbol=symbol,
                timeframe=timeframe,
            )
        except Exception as error:
            last_error = error

    assert last_error is not None
    raise last_error


async def http_json(url: str, *, max_retries: int) -> Any:
    delay = 0.5

    for attempt in range(max_retries + 1):
        try:
            return await asyncio.to_thread(read_json_url, url)
        except urllib.error.HTTPError as error:
            if error.code not in {418, 429, 500, 502, 503, 504}:
                raise
            if attempt >= max_retries:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt >= max_retries:
                raise

        await asyncio.sleep(delay)
        delay = min(delay * 2, 8)

    raise RuntimeError(f"Failed to fetch {url}")


def read_json_url(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "TickframeBackfill/1.0",
        },
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_binance_klines(
    payload: Sequence[Sequence[Any]],
    *,
    market_type: str,
    instrument_id: str,
    source_symbol: str,
    timeframe: str,
) -> List[HistoricalCandle]:
    interval_ms = INTERVAL_MS[timeframe]
    candles = []

    for row in payload:
        open_time_ms = int(row[0])
        base_volume = str(Decimal(str(row[5])))
        quote_volume = str(Decimal(str(row[7])))
        trade_count = int(row[8])

        candles.append(
            HistoricalCandle(
                exchange="binance",
                market_type=market_type,
                instrument_id=instrument_id,
                timeframe=timeframe,
                source="rest_klines",
                source_symbol=source_symbol,
                open_time_ms=open_time_ms,
                close_time_ms=open_time_ms + interval_ms,
                open=str(Decimal(str(row[1]))),
                high=str(Decimal(str(row[2]))),
                low=str(Decimal(str(row[3]))),
                close=str(Decimal(str(row[4]))),
                base_volume=base_volume,
                quote_volume=quote_volume,
                trade_count=trade_count,
                status="complete" if trade_count > 0 else "complete_empty",
                revision=1,
                finalized_at_ms=open_time_ms + interval_ms,
            )
        )

    return sorted(candles, key=lambda candle: candle.open_time_ms)


def parse_bybit_klines(
    payload: Dict[str, Any],
    *,
    market_type: str,
    instrument_id: str,
    source_symbol: str,
    timeframe: str,
) -> List[HistoricalCandle]:
    if int(payload.get("retCode", -1)) != 0:
        raise RuntimeError(f"Bybit error: {payload}")

    interval_ms = INTERVAL_MS[timeframe]
    candles = []

    for row in payload.get("result", {}).get("list", []):
        open_time_ms = int(row[0])
        base_volume = str(Decimal(str(row[5])))
        quote_volume = str(Decimal(str(row[6])))

        candles.append(
            HistoricalCandle(
                exchange="bybit",
                market_type=market_type,
                instrument_id=instrument_id,
                timeframe=timeframe,
                source="rest_klines",
                source_symbol=source_symbol,
                open_time_ms=open_time_ms,
                close_time_ms=open_time_ms + interval_ms,
                open=str(Decimal(str(row[1]))),
                high=str(Decimal(str(row[2]))),
                low=str(Decimal(str(row[3]))),
                close=str(Decimal(str(row[4]))),
                base_volume=base_volume,
                quote_volume=quote_volume,
                trade_count=0,
                status="complete_empty" if Decimal(base_volume) == 0 else "complete",
                revision=1,
                finalized_at_ms=open_time_ms + interval_ms,
            )
        )

    return sorted(candles, key=lambda candle: candle.open_time_ms)


def bybit_interval(timeframe: str) -> str:
    if timeframe == "1m":
        return "1"
    raise ValueError(f"Unsupported Bybit REST kline timeframe: {timeframe}")


def supports_rest_timeframe(exchange: str, timeframe: str) -> bool:
    return not (exchange == "bybit" and timeframe == "1s")


async def flush(
    pool: Optional[asyncpg.Pool],
    candles: List[HistoricalCandle],
    *,
    dry_run: bool,
) -> int:
    if not candles:
        return 0

    if dry_run:
        return len(candles)

    assert pool is not None

    rows = [candle_to_row(candle) for candle in candles]

    async with pool.acquire() as connection:
        await connection.executemany(
            """
            INSERT INTO historical_candles (
                exchange,
                market_type,
                instrument_id,
                timeframe,
                source,
                source_symbol,
                open_time,
                close_time,
                open,
                high,
                low,
                close,
                base_volume,
                quote_volume,
                trade_count,
                status,
                revision,
                finalized_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                to_timestamp($7 / 1000.0),
                to_timestamp($8 / 1000.0),
                $9, $10, $11, $12, $13, $14, $15, $16, $17,
                to_timestamp($18 / 1000.0)
            )
            ON CONFLICT (
                exchange,
                market_type,
                instrument_id,
                timeframe,
                open_time,
                source
            ) DO UPDATE SET
                source_symbol = EXCLUDED.source_symbol,
                close_time = EXCLUDED.close_time,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                base_volume = EXCLUDED.base_volume,
                quote_volume = EXCLUDED.quote_volume,
                trade_count = EXCLUDED.trade_count,
                status = EXCLUDED.status,
                revision = EXCLUDED.revision,
                finalized_at = EXCLUDED.finalized_at,
                imported_at = NOW()
            """,
            rows,
        )

    return len(candles)


def candle_to_row(candle: HistoricalCandle) -> tuple:
    return (
        candle.exchange,
        candle.market_type,
        candle.instrument_id,
        candle.timeframe,
        candle.source,
        candle.source_symbol,
        candle.open_time_ms,
        candle.close_time_ms,
        candle.open,
        candle.high,
        candle.low,
        candle.close,
        candle.base_volume,
        candle.quote_volume,
        candle.trade_count,
        candle.status,
        candle.revision,
        candle.finalized_at_ms,
    )


def align_closed_end_ms(until_ms: Optional[int], interval_ms: int) -> int:
    raw = until_ms if until_ms is not None else int(time.time() * 1000)
    return (raw // interval_ms) * interval_ms


def select_instruments(
    instruments: Iterable[InstrumentConfig],
    requested: str,
) -> List[InstrumentConfig]:
    values = list(instruments)

    if requested == "all":
        return values

    selected = [
        instrument
        for instrument in values
        if instrument.instrument_id == requested or instrument.base == requested
    ]

    if not selected:
        raise SystemExit(f"Unknown instrument: {requested}")

    return selected


def normalize_database_url(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    if value.startswith("postgresql+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgresql+asyncpg://")

    return value


def bybit_base_urls() -> Sequence[str]:
    configured = os.getenv("TICKFRAME_BYBIT_REST_URLS") or os.getenv(
        "TICKFRAME_BYBIT_BASE_URLS"
    )

    if configured:
        values = [value.strip() for value in configured.split(",") if value.strip()]
        if values:
            return values

    return DEFAULT_BYBIT_BASE_URLS


def binance_base_urls() -> Sequence[str]:
    configured = os.getenv("TICKFRAME_BINANCE_REST_URLS") or os.getenv(
        "TICKFRAME_BINANCE_BASE_URLS"
    )

    if configured:
        values = [value.strip() for value in configured.split(",") if value.strip()]
        if values:
            return values

    return BINANCE_BASE_URLS


if __name__ == "__main__":
    asyncio.run(main())
