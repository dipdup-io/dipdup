import asyncio
import logging
from typing import Awaitable
from typing import Callable


class Watchdog:
    """Simple keepalive task."""

    def __init__(self, timeout: float, fn: Callable[..., Awaitable[None]]) -> None:
        self._logger = logging.getLogger('watchdog')
        self._timeout = timeout
        self._fn = fn
        self._event = asyncio.Event()

    async def run(self) -> None:
        while True:
            try:
                await asyncio.wait_for(self._event.wait(), self._timeout)
                await asyncio.sleep(0)
            except asyncio.TimeoutError:
                self._logger.critical('Watchdog has timed out.')
                await self._fn()

    def reset(self) -> None:
        self._event.set()
        self._event.clear()
