import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

from backend.app.config import load_config
from backend.app.models import Trade
from backend.app.observability import LatencyObservability
from backend.app.store import LiveStore
from backend.scripts import check_critical_coverage


LATENCY_BUDGET_MS = 1_000
STALE_STATUS_BUDGET_MS = 10_000


def market_trade(latency_ms: int, trade_id: str = "1") -> Trade:
    exchange_timestamp_ms = 1_000_000
    return Trade(
        exchange="binance",
        market_type="spot",
        instrument_id="BTC-USDT",
        exchange_symbol="BTCUSDT",
        trade_id=trade_id,
        exchange_timestamp_ms=exchange_timestamp_ms,
        received_timestamp_ms=exchange_timestamp_ms + latency_ms,
        price=Decimal("64000.50"),
        base_quantity=Decimal("0.01"),
        side="buy",
    )


def find_latency(
    snapshot: dict[str, Any],
    *,
    stage: str,
    exchange: str,
    instrument_id: str,
) -> dict[str, Any]:
    for item in snapshot["latency"]:
        if (
            item["stage"] == stage
            and item["exchange"] == exchange
            and item["instrumentId"] == instrument_id
        ):
            return item
    raise AssertionError(f"Missing latency series: {stage} {exchange} {instrument_id}")


def find_market(
    snapshot: dict[str, Any],
    *,
    exchange: str,
    instrument_id: str,
) -> dict[str, Any]:
    for market in snapshot["markets"]:
        if market["exchange"] == exchange and market["instrumentId"] == instrument_id:
            return market
    raise AssertionError(f"Missing market: {exchange} {instrument_id}")


def coverage_payload(percent_covered: float) -> dict[str, Any]:
    return {
        "files": {
            module: {"summary": {"percent_covered": percent_covered}}
            for module in check_critical_coverage.CRITICAL_MODULES
        }
    }


def run_coverage_gate(payload: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        coverage_path = Path(tmpdir) / "coverage.json"
        coverage_path.write_text(json.dumps(payload), encoding="utf-8")
        with (
            patch.object(
                sys,
                "argv",
                ["check_critical_coverage.py", str(coverage_path)],
            ),
            patch("builtins.print"),
        ):
            check_critical_coverage.main()


class QualityRequirementLatencyTests(unittest.TestCase):
    def test_qrt_001_market_data_update_latency_budget(self) -> None:
        telemetry = LatencyObservability()
        latencies_ms = [750] * 19 + [1_200]

        for index, latency_ms in enumerate(latencies_ms, start=1):
            trade = market_trade(latency_ms, trade_id=str(index))
            telemetry.observe_trade(
                trade,
                processed_at_ms=trade.received_timestamp_ms + 10,
            )

        snapshot = telemetry.snapshot(now_ms=1_010_000)
        exchange_to_backend = find_latency(
            snapshot,
            stage="exchange_to_backend",
            exchange="binance",
            instrument_id="BTC-USDT",
        )
        within_budget = sum(
            1 for latency_ms in latencies_ms if latency_ms <= LATENCY_BUDGET_MS
        )

        self.assertEqual(exchange_to_backend["count"], len(latencies_ms))
        self.assertGreaterEqual(within_budget / len(latencies_ms), 0.95)
        self.assertLessEqual(exchange_to_backend["p95Ms"], LATENCY_BUDGET_MS)


class QualityRequirementFailureVisibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_qrt_002_exchange_failure_status_visible_within_budget(self) -> None:
        store = LiveStore(load_config())
        trade = market_trade(25)

        await store.apply_trade(trade)

        live_snapshot = await store.market_snapshot(
            now_ms=trade.received_timestamp_ms + STALE_STATUS_BUDGET_MS - 1,
        )
        stale_snapshot = await store.market_snapshot(
            now_ms=trade.received_timestamp_ms + STALE_STATUS_BUDGET_MS,
        )

        live_market = find_market(
            live_snapshot,
            exchange="binance",
            instrument_id="BTC-USDT",
        )
        stale_market = find_market(
            stale_snapshot,
            exchange="binance",
            instrument_id="BTC-USDT",
        )

        self.assertEqual(live_market["status"], "live")
        self.assertEqual(live_market["ageMs"], STALE_STATUS_BUDGET_MS - 1)
        self.assertEqual(stale_market["status"], "stale")
        self.assertEqual(stale_market["ageMs"], STALE_STATUS_BUDGET_MS)


class QualityRequirementCoverageGateTests(unittest.TestCase):
    def test_qrt_003_critical_coverage_gate_accepts_required_threshold(self) -> None:
        payload = coverage_payload(check_critical_coverage.MINIMUM_COVERAGE)

        run_coverage_gate(payload)

    def test_qrt_003_critical_coverage_gate_fails_below_threshold(self) -> None:
        payload = coverage_payload(check_critical_coverage.MINIMUM_COVERAGE)
        payload["files"]["backend/app/aggregation.py"]["summary"]["percent_covered"] = (
            check_critical_coverage.MINIMUM_COVERAGE - 0.01
        )

        with self.assertRaises(SystemExit) as raised:
            run_coverage_gate(payload)

        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
