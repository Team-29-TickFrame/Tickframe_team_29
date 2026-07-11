import os
from decimal import Decimal
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from backend.app import main
from backend.app.config import load_config
from backend.app.models import Trade
from backend.app.service import MarketDataService


class ApplicationLifespanTests(unittest.IsolatedAsyncioTestCase):
    async def test_lifespan_always_stops_services_after_runtime_error(self) -> None:
        auth = AsyncMock()
        market_service = AsyncMock()

        with (
            patch.object(main, "auth_service", auth),
            patch.object(main, "service", market_service),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("TICKFRAME_DISABLE_COLLECTORS", None)
            with self.assertRaisesRegex(RuntimeError, "runtime failed"):
                async with main.lifespan(main.app):
                    raise RuntimeError("runtime failed")

        auth.start.assert_awaited_once()
        market_service.start.assert_awaited_once()
        market_service.stop.assert_awaited_once()
        auth.stop.assert_awaited_once()

    async def test_auth_is_stopped_when_market_service_start_fails(self) -> None:
        auth = AsyncMock()
        market_service = AsyncMock()
        market_service.start.side_effect = RuntimeError("startup failed")

        with (
            patch.object(main, "auth_service", auth),
            patch.object(main, "service", market_service),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("TICKFRAME_DISABLE_COLLECTORS", None)
            with self.assertRaisesRegex(RuntimeError, "startup failed"):
                async with main.lifespan(main.app):
                    pass

        auth.stop.assert_awaited_once()
        market_service.stop.assert_not_awaited()

    async def test_auth_is_stopped_when_market_service_stop_fails(self) -> None:
        auth = AsyncMock()
        market_service = AsyncMock()
        market_service.stop.side_effect = RuntimeError("shutdown failed")

        with (
            patch.object(main, "auth_service", auth),
            patch.object(main, "service", market_service),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("TICKFRAME_DISABLE_COLLECTORS", None)
            with self.assertRaisesRegex(RuntimeError, "shutdown failed"):
                async with main.lifespan(main.app):
                    pass

        market_service.stop.assert_awaited_once()
        auth.stop.assert_awaited_once()


class MarketPipelineLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_trade_worker_continues_after_one_processing_failure(self) -> None:
        service = MarketDataService(load_config())
        service.store.apply_trade = AsyncMock(
            side_effect=[RuntimeError("bad trade"), None]
        )
        trades = [
            Trade(
                exchange="binance",
                market_type="spot",
                instrument_id="BTC-USDT",
                exchange_symbol="BTCUSDT",
                trade_id=str(index),
                exchange_timestamp_ms=1_000 + index,
                received_timestamp_ms=1_010 + index,
                price=Decimal("100"),
                base_quantity=Decimal("1"),
                side="buy",
            )
            for index in range(2)
        ]
        worker = asyncio.create_task(service._consume_trades())
        for trade in trades:
            await service.trade_queue.put(trade)

        with self.assertLogs("backend.app.service", level="ERROR"):
            await asyncio.wait_for(service.trade_queue.join(), timeout=1)

        self.assertFalse(worker.done())
        self.assertEqual(service.failed_trades, 1)
        self.assertEqual(service.processed_trades, 1)
        self.assertIsNone(service.last_trade_error)
        worker.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await worker


if __name__ == "__main__":
    unittest.main()
