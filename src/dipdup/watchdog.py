import asyncio
import logging
import time

from dipdup.config import WatchdogAction
from dipdup.config import WatchdogConfig
from dipdup.config import WatchdogTrigger
from dipdup.exceptions import WatchdogTimeoutError

_logger = logging.getLogger(__name__)

DEFAULT_WATCHDOGS = {
    WatchdogTrigger.callback: WatchdogConfig(action=WatchdogAction.warning, timeout=10),
    WatchdogTrigger.transaction: WatchdogConfig(action=WatchdogAction.warning, timeout=10),
    WatchdogTrigger.websocket: WatchdogConfig(action=WatchdogAction.warning, timeout=60),
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

    def initialize(self, config: dict[WatchdogTrigger, WatchdogConfig]) -> None:
        merged_config = {**DEFAULT_WATCHDOGS}
        for key, value in config.items():
            if value.timeout is not None:
                merged_config[key].timeout = value.timeout
            if value.action is not None:
                merged_config[key].action = value.action

        for trigger, watchdog_config in merged_config.items():
            self._watchdogs[trigger] = Watchdog(watchdog_config.timeout)  # type: ignore
            self._actions[trigger] = watchdog_config.action  # type: ignore

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
