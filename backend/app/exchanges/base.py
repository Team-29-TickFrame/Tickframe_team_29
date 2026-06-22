import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Dict, Optional

from ..models import Trade


LOGGER = logging.getLogger(__name__)
TradeHandler = Callable[[Trade], Awaitable[None]]
StateHandler = Callable[[str, bool, int], Awaitable[None]]


def unix_ms() -> int:
    return int(time.time() * 1000)


class ExchangeCollector(ABC):
    def __init__(
        self,
        name: str,
        on_trade: TradeHandler,
        on_state_change: Optional[StateHandler] = None,
    ) -> None:
        self.name = name
        self.on_trade = on_trade
        self.on_state_change = on_state_change
        self.connected = False
        self.last_error: Optional[str] = None
        self.last_message_at: Optional[int] = None
        self.active_endpoint: Optional[str] = None
        self.endpoint_failures = 0
        self.reconnects = 0
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(
                self.run(),
                name=f"{self.name}-market-collector",
            )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def run(self) -> None:
        backoff_seconds = 1
        while not self._stop_event.is_set():
            try:
                await self.connect_once()
                backoff_seconds = 1
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.connected = False
                self.last_error = str(error)
                self.reconnects += 1
                LOGGER.warning(
                    "%s connection failed; retrying in %ss: %s",
                    self.name,
                    backoff_seconds,
                    error,
                )
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=backoff_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
                backoff_seconds = min(backoff_seconds * 2, 30)

    @abstractmethod
    async def connect_once(self) -> None:
        raise NotImplementedError

    def is_instrument_active(self, instrument_id: str) -> bool:
        return self.connected

    async def set_connected(self, connected: bool) -> None:
        if self.connected == connected:
            return
        self.connected = connected
        if self.on_state_change is not None:
            await self.on_state_change(self.name, connected, unix_ms())

    def health(self) -> Dict[str, object]:
        now = unix_ms()
        message_age_ms = (
            now - self.last_message_at if self.last_message_at is not None else None
        )
        return {
            "exchange": self.name,
            "connected": self.connected,
            "lastMessageAt": self.last_message_at,
            "messageAgeMs": message_age_ms,
            "reconnects": self.reconnects,
            "endpoint": self.active_endpoint,
            "endpointFailures": self.endpoint_failures,
            "lastError": self.last_error,
        }
