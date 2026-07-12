from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import time
import urllib.request
from urllib.parse import quote
import zipfile
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence
from xml.etree import ElementTree

from .features import extract_features
from .weak_labeling import PATTERN_LABELS, label_window


BINANCE_BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DOWNLOAD_HOST = "https://data.binance.vision"
SOURCE_TIMEFRAME = "1m"
DEFAULT_DATASET_TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"]
SOURCE = "binance-public-data"
ONE_MINUTE_MS = 60_000
MICROSECOND_TIMESTAMP_THRESHOLD = 100_000_000_000_000
CSV_COLUMNS = [
    "openTime",
    "open",
    "high",
    "low",
    "close",
    "baseVolume",
    "closeTime",
    "quoteVolume",
    "tradeCount",
    "takerBuyBaseVolume",
    "takerBuyQuoteVolume",
    "ignore",
]


@dataclass(frozen=True)
class ArchiveItem:
    symbol: str
    key: str
    period: str
    kind: str
    size: int

    @property
    def url(self) -> str:
        return f"{DOWNLOAD_HOST}/{self.key}"


@dataclass(frozen=True)
class NormalizationStats:
    candle_count: int
    duplicate_count: int
    source_ms_rows: int
    source_us_rows: int
    first_open_time: Optional[int]
    latest_open_time: Optional[int]


@dataclass(frozen=True)
class FeatureRow:
    payload: Dict[str, object]
    label: str
    symbol: str
    open_time: int
    year: int
    is_hard_negative: bool


class BoundedCandidateSampler:
    def __init__(self, *, per_label_year_limit: int, seed: int) -> None:
        self.per_label_year_limit = per_label_year_limit
        self._rng = random.Random(seed)
        self._buckets: Dict[str, Dict[int, List[FeatureRow]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._seen: Counter[tuple[str, int]] = Counter()

    def add(self, row: FeatureRow) -> None:
        key = (row.label, row.year)
        self._seen[key] += 1
        bucket = self._buckets[row.label][row.year]
        if len(bucket) < self.per_label_year_limit:
            bucket.append(row)
            return
        replacement_index = self._rng.randrange(self._seen[key])
        if replacement_index < self.per_label_year_limit:
            bucket[replacement_index] = row

    def rows_by_label(self) -> Dict[str, List[FeatureRow]]:
        return {
            label: [
                row
                for year in sorted(years)
                for row in sorted(years[year], key=lambda item: item.open_time)
            ]
            for label, years in self._buckets.items()
        }

    def seen_counts_by_label(self) -> Dict[str, int]:
        counts: Counter[str] = Counter()
        for label, _year in self._seen:
            counts[label] += self._seen[(label, _year)]
        return dict(sorted(counts.items()))

    def sampled_count(self) -> int:
        return sum(
            len(rows) for years in self._buckets.values() for rows in years.values()
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download Binance public 1m spot klines and prepare weak-labeled "
            "feature examples for the Tickframe pattern model."
        )
    )
    parser.add_argument(
        "--config",
        default="ml/pattern_recognition/config.json",
        help="Training config with symbols, output paths, and labeling parameters.",
    )
    parser.add_argument(
        "--data-dir",
        default="data/ml/pattern_recognition/binance-public-spot-1m",
        help="Local directory for raw archives, normalized candles, and features.",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Override symbols from config, e.g. BTCUSDT ETHUSDT.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Optional inclusive end date in YYYY-MM-DD. Defaults to latest archive.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Use already downloaded archives and only rebuild prepared files.",
    )
    parser.add_argument(
        "--offline-normalized",
        action="store_true",
        help=(
            "Do not query Binance. Use existing normalized 1m CSV files and rebuild "
            "prepared feature datasets from them."
        ),
    )
    parser.add_argument(
        "--rebuild-normalized",
        action="store_true",
        help="Rebuild normalized per-symbol CSV files even if they already exist.",
    )
    parser.add_argument(
        "--timeframes",
        nargs="*",
        default=None,
        help="Prepared dataset timeframes, e.g. 1m 5m 15m 1h 1d.",
    )
    parser.add_argument(
        "--no-checksum",
        action="store_true",
        help="Skip Binance .CHECKSUM verification.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    symbols = args.symbols or list(config.get("symbols", []))
    if not symbols:
        raise ValueError("No Binance symbols configured.")

    window_size = int(config["windowSize"])
    stride = int(config.get("labeling", {}).get("stride", 12))
    max_examples_per_label = int(
        config.get("labeling", {}).get("maxExamplesPerLabel", 3000)
    )
    none_stride_multiplier = int(
        config.get("labeling", {}).get("noneStrideMultiplier", 8)
    )
    min_score = float(config.get("labeling", {}).get("minPatternScore", 0.58))
    hard_negative_min_score = float(
        config.get("labeling", {}).get("hardNegativeMinScore", 0.42)
    )
    candidate_cap_per_label_year = int(
        config.get("labeling", {}).get(
            "candidateCapPerLabelYear",
            max(500, min(max_examples_per_label, 1000)),
        )
    )
    timeframes = dataset_timeframes(config=config, args=args)
    end_date = _parse_date(args.end_date) if args.end_date else None

    data_dir = Path(args.data_dir)
    raw_dir = data_dir / "raw"
    normalized_dir = data_dir / "normalized"
    prepared_dir = Path(str(config.get("preparedDir", data_dir / "prepared")))
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "dataset": config["dataset"],
        "source": SOURCE,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceTimeframe": SOURCE_TIMEFRAME,
        "timeframes": timeframes,
        "windowSize": window_size,
        "stride": stride,
        "maxExamplesPerLabel": max_examples_per_label,
        "candidateCapPerLabelYear": candidate_cap_per_label_year,
        "hardNegativeMinScore": hard_negative_min_score,
        "symbols": {},
        "labels": list(config["labels"]),
        "featurePaths": {
            timeframe: str(feature_path_for(prepared_dir, timeframe))
            for timeframe in timeframes
        },
    }

    feature_paths = {
        timeframe: feature_path_for(prepared_dir, timeframe) for timeframe in timeframes
    }
    temporary_feature_paths = {
        timeframe: path.with_suffix(".jsonl.tmp")
        for timeframe, path in feature_paths.items()
    }
    totals: Dict[str, Counter[str]] = {timeframe: Counter() for timeframe in timeframes}
    feature_files = {
        timeframe: path.open("w", encoding="utf-8", newline="\n")
        for timeframe, path in temporary_feature_paths.items()
    }
    try:
        for symbol in symbols:
            normalized_path = normalized_dir / f"{symbol}-{SOURCE_TIMEFRAME}.csv"
            print(
                f"prepare symbol={symbol} load_normalized={normalized_path}", flush=True
            )
            archive_summary: Dict[str, object] = {}
            if not args.offline_normalized:
                monthly_archives = list_monthly_archives(symbol)
                daily_archives = list_daily_archives(symbol)
                if monthly_archives:
                    latest_monthly_end = _month_end(monthly_archives[-1].period)
                    daily_archives = [
                        item
                        for item in daily_archives
                        if _parse_date(item.period) > latest_monthly_end
                    ]
                archives = [*monthly_archives, *daily_archives]
                if end_date is not None:
                    archives = [
                        item for item in archives if _archive_start(item) <= end_date
                    ]
                if not archives:
                    manifest["symbols"][symbol] = {"status": "no_archives_found"}
                    continue

                local_archives = []
                for item in archives:
                    local_path = raw_dir / item.key
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    if not args.skip_download:
                        download_archive(
                            item,
                            local_path,
                            verify_checksum=not args.no_checksum,
                        )
                    if local_path.exists():
                        local_archives.append(local_path)

                archive_summary = {
                    "firstArchivePeriod": archives[0].period,
                    "latestArchivePeriod": archives[-1].period,
                    "archiveCount": len(local_archives),
                }
                if args.rebuild_normalized or not normalized_path.exists():
                    normalize_archives(local_archives, normalized_path)
            elif not normalized_path.exists():
                manifest["symbols"][symbol] = {
                    "status": "missing_normalized_file",
                    "normalizedPath": str(normalized_path),
                }
                continue

            source_candles, clean_stats = load_ordered_candles(normalized_path)
            print(
                f"loaded symbol={symbol} rows={clean_stats['rows']} "
                f"clean={len(source_candles)} backward_jumps={clean_stats['backwardJumpsBeforeSort']}",
                flush=True,
            )
            if args.offline_normalized and args.rebuild_normalized:
                rewrite_normalized_candles(source_candles, normalized_path)

            symbol_manifest: Dict[str, object] = {
                "status": "prepared",
                **archive_summary,
                "normalizedPath": str(normalized_path),
                "sourceCandleCount": clean_stats["rows"],
                "cleanCandleCount": len(source_candles),
                "normalization": clean_stats,
                "timeframes": {},
            }

            for timeframe in timeframes:
                print(
                    f"resample symbol={symbol} timeframe={timeframe} start "
                    f"source_candles={len(source_candles)}",
                    flush=True,
                )
                timeframe_candles = (
                    source_candles
                    if timeframe == SOURCE_TIMEFRAME
                    else resample_candles(source_candles, timeframe)
                )
                print(
                    f"resample symbol={symbol} timeframe={timeframe} done "
                    f"candles={len(timeframe_candles)}",
                    flush=True,
                )
                stats = prepare_features_from_candles(
                    timeframe_candles,
                    output=feature_files[timeframe],
                    timeframe=timeframe,
                    symbol=symbol,
                    window_size=window_size,
                    stride=stride,
                    max_examples_per_label=max_examples_per_label,
                    none_stride_multiplier=none_stride_multiplier,
                    min_score=min_score,
                    hard_negative_min_score=hard_negative_min_score,
                    candidate_cap_per_label_year=candidate_cap_per_label_year,
                )
                totals[timeframe].update(stats["labelCounts"])
                feature_files[timeframe].flush()
                symbol_manifest["timeframes"][timeframe] = {
                    "candleCount": len(timeframe_candles),
                    **stats,
                }
                print(
                    f"prepared symbol={symbol} timeframe={timeframe} "
                    f"candles={len(timeframe_candles)} examples={sum(stats['labelCounts'].values())} "
                    f"labels={stats['labelCounts']}",
                    flush=True,
                )

            manifest["symbols"][symbol] = symbol_manifest
    finally:
        for handle in feature_files.values():
            handle.close()

    for timeframe, temporary_path in temporary_feature_paths.items():
        replace_file(temporary_path, feature_paths[timeframe])

    manifest["classCounts"] = {
        timeframe: dict(sorted(counter.items()))
        for timeframe, counter in sorted(totals.items())
    }
    manifest["totalExamples"] = {
        timeframe: sum(counter.values())
        for timeframe, counter in sorted(totals.items())
    }
    manifest_path = prepared_dir / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(
        "prepared "
        f"dataset={config['dataset']} "
        f"timeframes={','.join(timeframes)} "
        f"examples={manifest['totalExamples']} "
        f"manifest={manifest_path}"
    )


def dataset_timeframes(
    *, config: Dict[str, object], args: argparse.Namespace
) -> List[str]:
    configured = args.timeframes or config.get("datasetTimeframes")
    if configured is None:
        configured = [str(config.get("timeframe", SOURCE_TIMEFRAME))]
    timeframes = [str(timeframe) for timeframe in configured]
    if not timeframes:
        return [SOURCE_TIMEFRAME]
    for timeframe in timeframes:
        timeframe_to_ms(timeframe)
    return timeframes


def feature_path_for(prepared_dir: Path, timeframe: str) -> Path:
    if timeframe == SOURCE_TIMEFRAME:
        return prepared_dir / "features.jsonl"
    return prepared_dir / f"features-{timeframe}.jsonl"


def list_monthly_archives(symbol: str) -> List[ArchiveItem]:
    prefix = f"data/spot/monthly/klines/{symbol}/{SOURCE_TIMEFRAME}/"
    archives: List[ArchiveItem] = []
    pattern = re.compile(
        rf"{re.escape(symbol)}-{SOURCE_TIMEFRAME}-(\d{{4}}-\d{{2}})\.zip$"
    )
    for key, size in list_s3_keys(prefix):
        match = pattern.search(key)
        if not match:
            continue
        archives.append(
            ArchiveItem(
                symbol=symbol,
                key=key,
                period=match.group(1),
                kind="monthly",
                size=size,
            )
        )
    return sorted(archives, key=lambda item: item.period)


def list_daily_archives(symbol: str) -> List[ArchiveItem]:
    prefix = f"data/spot/daily/klines/{symbol}/{SOURCE_TIMEFRAME}/"
    archives: List[ArchiveItem] = []
    pattern = re.compile(
        rf"{re.escape(symbol)}-{SOURCE_TIMEFRAME}-(\d{{4}}-\d{{2}}-\d{{2}})\.zip$"
    )
    for key, size in list_s3_keys(prefix):
        match = pattern.search(key)
        if not match:
            continue
        archives.append(
            ArchiveItem(
                symbol=symbol,
                key=key,
                period=match.group(1),
                kind="daily",
                size=size,
            )
        )
    return sorted(archives, key=lambda item: item.period)


def list_s3_keys(prefix: str) -> Iterator[tuple[str, int]]:
    token: Optional[str] = None
    namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    while True:
        url = f"{BINANCE_BUCKET}?list-type=2&prefix={quote(prefix)}"
        if token:
            url += f"&continuation-token={quote(token, safe='')}"
        content = _urlopen_bytes(url).decode("utf-8")
        root = ElementTree.fromstring(content)
        for content_node in root.findall("s3:Contents", namespace):
            key_node = content_node.find("s3:Key", namespace)
            size_node = content_node.find("s3:Size", namespace)
            if key_node is None or size_node is None:
                continue
            yield key_node.text or "", int(size_node.text or "0")

        truncated_node = root.find("s3:IsTruncated", namespace)
        if truncated_node is None or truncated_node.text != "true":
            break
        token_node = root.find("s3:NextContinuationToken", namespace)
        if token_node is None or not token_node.text:
            break
        token = token_node.text


def download_archive(
    item: ArchiveItem, local_path: Path, *, verify_checksum: bool
) -> None:
    if local_path.exists() and local_path.stat().st_size == item.size:
        if not verify_checksum or checksum_matches(item, local_path):
            return

    print(f"download {item.symbol} {item.period} {item.url}")
    payload = _urlopen_bytes(item.url)
    local_path.write_bytes(payload)
    if verify_checksum and not checksum_matches(item, local_path):
        raise ValueError(f"Checksum verification failed for {local_path}")


def checksum_matches(item: ArchiveItem, local_path: Path) -> bool:
    checksum_url = f"{item.url}.CHECKSUM"
    expected_payload = _urlopen_bytes(checksum_url).decode("utf-8").strip()
    expected = expected_payload.split()[0].lower()
    digest = hashlib.sha256(local_path.read_bytes()).hexdigest().lower()
    return digest == expected


def normalize_archives(
    archives: Sequence[Path],
    output_path: Path,
) -> NormalizationStats:
    candles_by_open_time: Dict[int, Dict[str, object]] = {}
    duplicate_count = 0
    source_ms_rows = 0
    source_us_rows = 0
    for archive in sorted(archives):
        with zipfile.ZipFile(archive) as zipped:
            for member in sorted(zipped.namelist()):
                if not member.endswith(".csv"):
                    continue
                with zipped.open(member) as csv_file:
                    text = (
                        line.decode("utf-8").strip()
                        for line in csv_file
                        if line.strip()
                    )
                    for row in csv.reader(text):
                        if not row or row[0] == "open_time":
                            continue
                        raw_open_time = int(row[0])
                        if raw_open_time >= MICROSECOND_TIMESTAMP_THRESHOLD:
                            source_us_rows += 1
                        else:
                            source_ms_rows += 1
                        candle = _normalize_row(row)
                        open_time = int(candle["openTime"])
                        if open_time in candles_by_open_time:
                            duplicate_count += 1
                        candles_by_open_time[open_time] = candle

    candles = [
        candles_by_open_time[open_time] for open_time in sorted(candles_by_open_time)
    ]
    rewrite_normalized_candles(candles, output_path)
    return NormalizationStats(
        candle_count=len(candles),
        duplicate_count=duplicate_count,
        source_ms_rows=source_ms_rows,
        source_us_rows=source_us_rows,
        first_open_time=int(candles[0]["openTime"]) if candles else None,
        latest_open_time=int(candles[-1]["openTime"]) if candles else None,
    )


def replace_file(source: Path, target: Path) -> None:
    for attempt in range(10):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.5)


def load_ordered_candles(
    path: Path,
) -> tuple[List[Dict[str, object]], Dict[str, object]]:
    candles_by_open_time: Dict[int, Dict[str, object]] = {}
    duplicate_count = 0
    source_ms_rows = 0
    source_us_rows = 0
    backward_jumps = 0
    previous_open_time: Optional[int] = None
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows += 1
            raw_open_time = int(row["openTime"])
            if raw_open_time >= MICROSECOND_TIMESTAMP_THRESHOLD:
                source_us_rows += 1
            else:
                source_ms_rows += 1
            open_time = timestamp_to_ms(raw_open_time)
            if previous_open_time is not None and open_time < previous_open_time:
                backward_jumps += 1
            previous_open_time = open_time
            candle = {
                "openTime": open_time,
                "closeTime": timestamp_to_ms(int(row["closeTime"])),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "baseVolume": float(row["baseVolume"]),
                "quoteVolume": float(row["quoteVolume"]),
                "tradeCount": int(row["tradeCount"]),
                "timeframe": SOURCE_TIMEFRAME,
                "status": row.get("status", "complete"),
            }
            if open_time in candles_by_open_time:
                duplicate_count += 1
            candles_by_open_time[open_time] = candle

    candles = [
        candles_by_open_time[open_time] for open_time in sorted(candles_by_open_time)
    ]
    return candles, {
        "rows": rows,
        "duplicateOpenTimes": duplicate_count,
        "sourceMsRows": source_ms_rows,
        "sourceUsRows": source_us_rows,
        "backwardJumpsBeforeSort": backward_jumps,
        "firstOpenTime": candles[0]["openTime"] if candles else None,
        "latestOpenTime": candles[-1]["openTime"] if candles else None,
    }


def rewrite_normalized_candles(
    candles: Sequence[Dict[str, object]],
    output_path: Path,
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=[
                "openTime",
                "closeTime",
                "open",
                "high",
                "low",
                "close",
                "baseVolume",
                "quoteVolume",
                "tradeCount",
                "timeframe",
                "status",
            ],
        )
        writer.writeheader()
        for candle in candles:
            writer.writerow(candle)


def resample_candles(
    candles: Sequence[Dict[str, object]],
    timeframe: str,
) -> List[Dict[str, object]]:
    timeframe_ms = timeframe_to_ms(timeframe)
    if timeframe_ms == ONE_MINUTE_MS:
        return list(candles)
    if timeframe_ms % ONE_MINUTE_MS != 0:
        raise ValueError(f"Unsupported non-minute timeframe: {timeframe}")

    expected_count = timeframe_ms // ONE_MINUTE_MS
    output: List[Dict[str, object]] = []
    bucket: List[Dict[str, object]] = []
    bucket_start: Optional[int] = None
    previous_open_time: Optional[int] = None
    for candle in candles:
        open_time = int(candle["openTime"])
        if (
            previous_open_time is not None
            and open_time - previous_open_time != ONE_MINUTE_MS
        ):
            bucket = []
            bucket_start = None
        previous_open_time = open_time

        start = (open_time // timeframe_ms) * timeframe_ms
        if bucket_start is None or start != bucket_start:
            if len(bucket) == expected_count:
                output.append(_aggregate_bucket(bucket, timeframe=timeframe))
            bucket = []
            bucket_start = start
        bucket.append(candle)

    if len(bucket) == expected_count:
        output.append(_aggregate_bucket(bucket, timeframe=timeframe))
    return output


def prepare_features_from_candles(
    candles: Sequence[Dict[str, object]],
    *,
    output,
    timeframe: str,
    symbol: str,
    window_size: int,
    stride: int,
    max_examples_per_label: int,
    none_stride_multiplier: int,
    min_score: float,
    hard_negative_min_score: float,
    candidate_cap_per_label_year: int,
) -> Dict[str, object]:
    candidates = BoundedCandidateSampler(
        per_label_year_limit=candidate_cap_per_label_year,
        seed=_stable_seed(f"{symbol}:{timeframe}"),
    )
    skipped_gap_windows = 0
    scanned_windows = 0
    timeframe_ms = timeframe_to_ms(timeframe)
    total_candles = len(candles)
    progress_step = max(1, total_candles // 10)
    next_progress_at = progress_step
    started_at = time.perf_counter()

    window: deque[Dict[str, object]] = deque(maxlen=window_size)
    previous_open_time: Optional[int] = None
    seen = 0
    for candle_index, candle in enumerate(candles, start=1):
        open_time = int(candle["openTime"])
        if (
            previous_open_time is not None
            and open_time - previous_open_time != timeframe_ms
        ):
            skipped_gap_windows += max(0, len(window) - window_size + 1)
            window.clear()
        previous_open_time = open_time
        window.append(candle)
        if candle_index >= next_progress_at or candle_index == total_candles:
            elapsed = max(0.001, time.perf_counter() - started_at)
            percent = candle_index / max(1, total_candles) * 100
            print(
                f"progress symbol={symbol} timeframe={timeframe} "
                f"candles={candle_index}/{total_candles} ({percent:.1f}%) "
                f"scanned_windows={scanned_windows} "
                f"sampled_candidates={candidates.sampled_count()} "
                f"seen={candidates.seen_counts_by_label()} "
                f"elapsed_s={elapsed:.1f}",
                flush=True,
            )
            while next_progress_at <= candle_index:
                next_progress_at += progress_step
        if len(window) < window_size:
            continue
        seen += 1
        if seen % stride != 0:
            continue

        candle_window = list(window)
        if not is_contiguous_window(candle_window, timeframe_ms):
            skipped_gap_windows += 1
            continue
        scanned_windows += 1
        weak_label = label_window(candle_window)
        max_soft_score = max(weak_label.label_scores.values(), default=0.0)
        if weak_label.label == "none":
            if max_soft_score >= hard_negative_min_score:
                hard_negative_for = weak_label.hard_negative_for
            else:
                hard_negative_for = None
                if seen % (stride * none_stride_multiplier) != 0:
                    continue
        elif weak_label.score < min_score:
            continue
        else:
            hard_negative_for = None

        features = extract_features(candle_window)
        payload = {
            "source": SOURCE,
            "symbol": symbol,
            "timeframe": timeframe,
            "label": weak_label.label,
            "score": weak_label.score,
            "labelScores": {
                label: round(float(weak_label.label_scores.get(label, 0.0)), 6)
                for label in PATTERN_LABELS
            },
            "softScores": {
                f"{label}_score": round(
                    float(weak_label.label_scores.get(label, 0.0)), 6
                )
                for label in PATTERN_LABELS
            },
            "hardNegativeFor": hard_negative_for,
            "anchors": weak_label.anchors,
            "reason": weak_label.reason,
            "openTime": int(candle_window[0]["openTime"]),
            "closeTime": int(candle_window[-1]["closeTime"]),
            "features": features,
        }
        row = FeatureRow(
            payload=payload,
            label=weak_label.label,
            symbol=symbol,
            open_time=int(candle_window[0]["openTime"]),
            year=datetime.fromtimestamp(
                int(candle_window[0]["openTime"]) / 1000,
                tz=timezone.utc,
            ).year,
            is_hard_negative=hard_negative_for is not None,
        )
        candidates.add(row)

    selected: List[FeatureRow] = []
    sampled_candidates = candidates.rows_by_label()
    for label, rows in sampled_candidates.items():
        selected.extend(sample_evenly_by_year(rows, max_examples_per_label))
    selected.sort(key=lambda row: (row.open_time, row.symbol, row.label))
    for row in selected:
        output.write(json.dumps(row.payload, sort_keys=True) + "\n")

    label_counts = Counter(row.label for row in selected)
    hard_negative_counts = Counter(
        str(row.payload["hardNegativeFor"])
        for row in selected
        if row.payload.get("hardNegativeFor")
    )
    year_counts = Counter(str(row.year) for row in selected)
    return {
        "labelCounts": dict(sorted(label_counts.items())),
        "candidateCounts": candidates.seen_counts_by_label(),
        "sampledCandidateCounts": {
            label: len(rows) for label, rows in sorted(sampled_candidates.items())
        },
        "candidateCapPerLabelYear": candidate_cap_per_label_year,
        "hardNegativeCounts": dict(sorted(hard_negative_counts.items())),
        "yearCounts": dict(sorted(year_counts.items())),
        "scannedWindows": scanned_windows,
        "skippedGapWindows": skipped_gap_windows,
    }


def _normalize_row(row: Sequence[str]) -> Dict[str, object]:
    values = dict(zip(CSV_COLUMNS, row))
    open_time = timestamp_to_ms(int(values["openTime"]))
    close_time = timestamp_to_ms(int(values["closeTime"]))
    return {
        "openTime": open_time,
        "closeTime": close_time,
        "open": values["open"],
        "high": values["high"],
        "low": values["low"],
        "close": values["close"],
        "baseVolume": values["baseVolume"],
        "quoteVolume": values["quoteVolume"],
        "tradeCount": int(values["tradeCount"]),
        "timeframe": SOURCE_TIMEFRAME,
        "status": "complete",
    }


def timestamp_to_ms(value: int) -> int:
    if value >= MICROSECOND_TIMESTAMP_THRESHOLD:
        return value // 1000
    return value


def timeframe_to_ms(timeframe: str) -> int:
    match = re.fullmatch(r"(\d+)(m|h|d|w)", timeframe)
    if not match:
        raise ValueError(
            f"Unsupported timeframe {timeframe!r}. Use values like 1m, 5m, 1h, 1d."
        )
    amount = int(match.group(1))
    unit = match.group(2)
    multipliers = {
        "m": ONE_MINUTE_MS,
        "h": 60 * ONE_MINUTE_MS,
        "d": 24 * 60 * ONE_MINUTE_MS,
        "w": 7 * 24 * 60 * ONE_MINUTE_MS,
    }
    return amount * multipliers[unit]


def _aggregate_bucket(
    bucket: Sequence[Dict[str, object]],
    *,
    timeframe: str,
) -> Dict[str, object]:
    return {
        "openTime": int(bucket[0]["openTime"]),
        "closeTime": int(bucket[-1]["closeTime"]),
        "open": float(bucket[0]["open"]),
        "high": max(float(candle["high"]) for candle in bucket),
        "low": min(float(candle["low"]) for candle in bucket),
        "close": float(bucket[-1]["close"]),
        "baseVolume": sum(float(candle["baseVolume"]) for candle in bucket),
        "quoteVolume": sum(float(candle["quoteVolume"]) for candle in bucket),
        "tradeCount": sum(int(candle["tradeCount"]) for candle in bucket),
        "timeframe": timeframe,
        "status": "complete",
    }


def is_contiguous_window(
    candles: Sequence[Dict[str, object]],
    timeframe_ms: int,
) -> bool:
    return all(
        int(right["openTime"]) - int(left["openTime"]) == timeframe_ms
        for left, right in zip(candles, candles[1:])
    )


def sample_evenly_by_year(
    rows: Sequence[FeatureRow],
    limit: int,
) -> List[FeatureRow]:
    if len(rows) <= limit:
        return sorted(rows, key=lambda row: row.open_time)
    by_year: Dict[int, List[FeatureRow]] = defaultdict(list)
    for row in rows:
        by_year[row.year].append(row)
    for year_rows in by_year.values():
        year_rows.sort(key=lambda row: row.open_time)

    years = sorted(by_year)
    selected: List[FeatureRow] = []
    cursors = {year: 0 for year in years}
    while len(selected) < limit:
        progressed = False
        for year in years:
            year_rows = by_year[year]
            cursor = cursors[year]
            if cursor >= len(year_rows):
                continue
            selected.append(year_rows[cursor])
            cursors[year] += max(1, round(len(year_rows) / max(1, limit // len(years))))
            progressed = True
            if len(selected) >= limit:
                break
        if not progressed:
            break

    if len(selected) < limit:
        selected_keys = {id(row) for row in selected}
        remaining = [
            row
            for row in sorted(rows, key=lambda item: item.open_time)
            if id(row) not in selected_keys
        ]
        selected.extend(remaining[: limit - len(selected)])
    return sorted(selected[:limit], key=lambda row: row.open_time)


def _stable_seed(value: str) -> int:
    seed = 0
    for char in value:
        seed = (seed * 131 + ord(char)) % (2**32)
    return seed


def _urlopen_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Tickframe ML dataset"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _archive_start(item: ArchiveItem) -> date:
    if item.kind == "daily":
        return _parse_date(item.period)
    return date.fromisoformat(f"{item.period}-01")


def _month_end(value: str) -> date:
    start = date.fromisoformat(f"{value}-01")
    if start.month == 12:
        return date(start.year, 12, 31)
    next_month = date(start.year, start.month + 1, 1)
    return date.fromordinal(next_month.toordinal() - 1)


if __name__ == "__main__":
    main()
