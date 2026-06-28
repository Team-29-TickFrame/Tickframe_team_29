from __future__ import annotations

import json
import sys
from pathlib import Path


MINIMUM_COVERAGE = 30.0
CRITICAL_MODULES = [
    "backend/app/aggregation.py",
    "backend/app/auth.py",
    "backend/app/exchanges/binance.py",
    "backend/app/exchanges/bybit.py",
    "backend/app/history.py",
    "backend/app/metrics.py",
    "backend/app/pattern_ml.py",
    "ml/pattern_recognition/dataset.py",
    "ml/pattern_recognition/features.py",
    "ml/pattern_recognition/model.py",
]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_critical_coverage.py coverage.json")

    coverage_path = Path(sys.argv[1])
    payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    files = payload.get("files", {})
    failures: list[str] = []

    for module in CRITICAL_MODULES:
        entry = files.get(module)
        if entry is None:
            failures.append(f"{module}: missing from coverage report")
            continue
        percent = float(entry["summary"]["percent_covered"])
        if percent < MINIMUM_COVERAGE:
            failures.append(f"{module}: {percent:.2f}% < {MINIMUM_COVERAGE:.2f}%")

    if failures:
        print("Critical module coverage check failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(
        "Critical module coverage check passed "
        f"for {len(CRITICAL_MODULES)} modules at >= {MINIMUM_COVERAGE:.0f}%."
    )


if __name__ == "__main__":
    main()
