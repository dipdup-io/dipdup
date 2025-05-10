import asyncio
import logging
import time

from dipdup.config import WatchdogAction
from dipdup.config import WatchdogTrigger
from dipdup.exceptions import WatchdogTimeoutError

_logger = logging.getLogger(__name__)

DEFAULT_WATCHDOGS = {
    WatchdogTrigger.callback: (WatchdogAction.warning, 10),
    WatchdogTrigger.transaction: (WatchdogAction.warning, 10),
    WatchdogTrigger.websocket: (WatchdogAction.warning, 60),
}


class Watchdog:
    def __init__(self, timeout: int) -> None:
        self._timeout = timeout
        self._timestamp = 0.0

    def heartbeat(self) -> None:
        self._timestamp = time.time()

    def reset(self) -> None:
        self._timestamp = 0.0

    def check(self) -> bool:
        if not self._timestamp or not self._timeout:
            return True
        if time.time() - self._timestamp < self._timeout:
            return True
        return False


class WatchdogManager:
    def __init__(self) -> None:
        self._watchdogs: dict[WatchdogTrigger, Watchdog] = {}
        self._actions: dict[WatchdogTrigger, WatchdogAction] = {}

    def register(
        self,
        trigger: WatchdogTrigger,
        action: WatchdogAction,
        timeout: int,
    ) -> None:
        self._watchdogs[trigger] = Watchdog(timeout)
        self._actions[trigger] = action

    async def run(self, interval: int) -> None:
        while True:
            for trigger, watchdog in self._watchdogs.items():
                if watchdog.check():
                    continue

                msg = f'`{trigger.value}` watchdog timeout! No activity in {int(time.time() - watchdog._timestamp)} seconds'
                action = self._actions[trigger]
                if action == WatchdogAction.warning:
                    _logger.warning(msg)
                elif action == WatchdogAction.exception:
                    raise WatchdogTimeoutError(msg)
                elif action == WatchdogAction.ignore:
                    _logger.debug('%s, ignoring', msg)
                else:
                    raise NotImplementedError(f'Unsupported watchdog action: {action}')

            await asyncio.sleep(interval)

    def heartbeat(self, trigger: WatchdogTrigger) -> None:
        if trigger not in self._watchdogs:
            return
        self._watchdogs[trigger].heartbeat()

    def reset(self, trigger: WatchdogTrigger) -> None:
        if trigger not in self._watchdogs:
            return
        self._watchdogs[trigger].reset()


# NOTE: Use this singleton from everywhere
watchdog = WatchdogManager()
