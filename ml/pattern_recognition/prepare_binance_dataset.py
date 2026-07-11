from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import urllib.request
from urllib.parse import quote
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence
from xml.etree import ElementTree

from .features import extract_features
from .weak_labeling import label_window


BINANCE_BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DOWNLOAD_HOST = "https://data.binance.vision"
TIMEFRAME = "1m"
SOURCE = "binance-public-data"
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
        "--rebuild-normalized",
        action="store_true",
        help="Rebuild normalized per-symbol CSV files even if they already exist.",
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
    end_date = _parse_date(args.end_date) if args.end_date else None

    data_dir = Path(args.data_dir)
    raw_dir = data_dir / "raw"
    normalized_dir = data_dir / "normalized"
    prepared_dir = data_dir / "prepared"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "dataset": config["dataset"],
        "source": SOURCE,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "timeframe": config["timeframe"],
        "windowSize": window_size,
        "stride": stride,
        "maxExamplesPerLabel": max_examples_per_label,
        "symbols": {},
        "labels": list(config["labels"]),
        "featurePath": str(prepared_dir / "features.jsonl"),
    }

    feature_path = prepared_dir / "features.jsonl"
    temporary_feature_path = feature_path.with_suffix(".jsonl.tmp")
    totals: Dict[str, int] = defaultdict(int)
    with temporary_feature_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as feature_file:
        for symbol in symbols:
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

            first_period = archives[0].period
            latest_period = archives[-1].period
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

            normalized_path = normalized_dir / f"{symbol}-{TIMEFRAME}.csv"
            if normalized_path.exists() and not args.rebuild_normalized:
                candle_count = count_normalized_candles(normalized_path)
            else:
                candle_count = normalize_archives(local_archives, normalized_path)
            label_counts = prepare_features(
                normalized_path,
                symbol=symbol,
                window_size=window_size,
                stride=stride,
                max_examples_per_label=max_examples_per_label,
                none_stride_multiplier=none_stride_multiplier,
                min_score=min_score,
                output=feature_file,
            )
            for label, count in label_counts.items():
                totals[label] += count
            feature_file.flush()

            manifest["symbols"][symbol] = {
                "status": "prepared",
                "firstArchivePeriod": first_period,
                "latestArchivePeriod": latest_period,
                "archiveCount": len(local_archives),
                "normalizedPath": str(normalized_path),
                "candleCount": candle_count,
                "labelCounts": dict(sorted(label_counts.items())),
            }

    manifest["classCounts"] = dict(sorted(totals.items()))
    manifest["totalExamples"] = sum(totals.values())
    replace_file(temporary_feature_path, feature_path)
    manifest_path = prepared_dir / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(
        "prepared "
        f"dataset={config['dataset']} "
        f"examples={manifest['totalExamples']} "
        f"features={feature_path} "
        f"manifest={manifest_path}"
    )


def list_monthly_archives(symbol: str) -> List[ArchiveItem]:
    prefix = f"data/spot/monthly/klines/{symbol}/{TIMEFRAME}/"
    archives: List[ArchiveItem] = []
    pattern = re.compile(rf"{re.escape(symbol)}-{TIMEFRAME}-(\d{{4}}-\d{{2}})\.zip$")
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
    prefix = f"data/spot/daily/klines/{symbol}/{TIMEFRAME}/"
    archives: List[ArchiveItem] = []
    pattern = re.compile(
        rf"{re.escape(symbol)}-{TIMEFRAME}-(\d{{4}}-\d{{2}}-\d{{2}})\.zip$"
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


def normalize_archives(archives: Sequence[Path], output_path: Path) -> int:
    count = 0
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
                            candle = _normalize_row(row)
                            writer.writerow(candle)
                            count += 1
    return count


def count_normalized_candles(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def replace_file(source: Path, target: Path) -> None:
    for attempt in range(10):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.5)


def prepare_features(
    normalized_path: Path,
    *,
    symbol: str,
    window_size: int,
    stride: int,
    max_examples_per_label: int,
    none_stride_multiplier: int,
    min_score: float,
    output,
) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    window: deque[Dict[str, object]] = deque(maxlen=window_size)
    seen = 0
    for candle in iter_normalized_candles(normalized_path):
        window.append(candle)
        if len(window) < window_size:
            continue
        seen += 1
        if seen % stride != 0:
            continue

        candles = list(window)
        weak_label = label_window(candles)
        if weak_label.label == "none":
            if seen % (stride * none_stride_multiplier) != 0:
                continue
        elif weak_label.score < min_score:
            continue

        label = weak_label.label
        if counts[label] >= max_examples_per_label:
            continue

        output.write(
            json.dumps(
                {
                    "source": SOURCE,
                    "symbol": symbol,
                    "timeframe": TIMEFRAME,
                    "label": label,
                    "score": weak_label.score,
                    "anchors": weak_label.anchors,
                    "reason": weak_label.reason,
                    "openTime": int(candles[0]["openTime"]),
                    "closeTime": int(candles[-1]["closeTime"]),
                    "features": extract_features(candles),
                },
                sort_keys=True,
            )
            + "\n"
        )
        counts[label] += 1

    return counts


def iter_normalized_candles(path: Path) -> Iterator[Dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            yield {
                "openTime": int(row["openTime"]),
                "closeTime": int(row["closeTime"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "baseVolume": float(row["baseVolume"]),
                "quoteVolume": float(row["quoteVolume"]),
                "tradeCount": int(row["tradeCount"]),
                "timeframe": row["timeframe"],
                "status": row["status"],
            }


def _normalize_row(row: Sequence[str]) -> Dict[str, object]:
    values = dict(zip(CSV_COLUMNS, row))
    return {
        "openTime": int(values["openTime"]),
        "closeTime": int(values["closeTime"]),
        "open": values["open"],
        "high": values["high"],
        "low": values["low"],
        "close": values["close"],
        "baseVolume": values["baseVolume"],
        "quoteVolume": values["quoteVolume"],
        "tradeCount": int(values["tradeCount"]),
        "timeframe": TIMEFRAME,
        "status": "complete",
    }


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
