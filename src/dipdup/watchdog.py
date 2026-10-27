import asyncio
import logging
import time
import traceback
from collections.abc import Hashable
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dipdup.config import WatchdogAction
from dipdup.config import WatchdogConfig
from dipdup.config import WatchdogTrigger
from dipdup.exceptions import WatchdogTimeoutError

if TYPE_CHECKING:
    from types import FrameType

_logger = logging.getLogger(__name__)

DEFAULT_WATCHDOGS = {
    WatchdogTrigger.callback: WatchdogConfig(action=WatchdogAction.warning, timeout=10),
    WatchdogTrigger.transaction: WatchdogConfig(action=WatchdogAction.warning, timeout=10),
    WatchdogTrigger.websocket: WatchdogConfig(action=WatchdogAction.warning, timeout=60),
}


@dataclass(eq=False)
class Activity:
    """Something the watchdog waits to finish (a callback, a transaction) or to show signs of life (a connection)"""

    name: str
    started_at: float
    task: asyncio.Task[object] | None = None
    reported: bool = False
    finished: bool = False


# NOTE: Activities watched in the current context, outermost first; tasks spawned inside inherit them
_current: ContextVar[tuple[tuple[WatchdogTrigger, Activity], ...]] = ContextVar('_current', default=())


def format_task_stack(task: asyncio.Task[object]) -> str:
    """Format the chain of coroutines the task is awaiting, outermost first.

    `Task.get_stack()` returns only the outermost frame of a suspended task.
    """
    frames: list[tuple[FrameType, int]] = []
    awaitable = task.get_coro()
    while awaitable is not None:
        frame = getattr(awaitable, 'cr_frame', None) or getattr(awaitable, 'gi_frame', None)
        if frame is None:
            break
        frames.append((frame, frame.f_lineno))
        awaitable = getattr(awaitable, 'cr_await', None) or getattr(awaitable, 'gi_yieldfrom', None)
    return ''.join(traceback.StackSummary.extract(iter(frames)).format()).rstrip()


class Watchdog:
    def __init__(self, timeout: int) -> None:
        self._timeout = timeout
        self._activities: dict[Hashable, Activity] = {}

    def start(self, key: Hashable, activity: Activity) -> None:
        self._activities[key] = activity

    def stop(self, key: Hashable) -> None:
        self._activities.pop(key, None)

    def overdue(self) -> list[Activity]:
        """Activities running longer than the timeout, oldest first"""
        if not self._timeout:
            return []
        deadline = time.time() - self._timeout
        return sorted(
            (a for a in self._activities.values() if a.started_at <= deadline),
            key=lambda a: a.started_at,
        )

    def activities(self) -> Iterator[Activity]:
        yield from self._activities.values()


class WatchdogManager:
    def __init__(self) -> None:
        self._watchdogs: dict[WatchdogTrigger, Watchdog] = {}
        self._actions: dict[WatchdogTrigger, WatchdogAction] = {}

    def initialize(self, config: dict[WatchdogTrigger, WatchdogConfig]) -> None:
        # NOTE: Merge into new objects; defaults are shared by every `initialize` call
        for trigger, default in DEFAULT_WATCHDOGS.items():
            value = config.get(trigger, default)
            timeout = default.timeout if value.timeout is None else value.timeout
            self._watchdogs[trigger] = Watchdog(timeout)  # type: ignore[arg-type]
            self._actions[trigger] = value.action or default.action  # type: ignore[assignment]

    async def run(self, interval: float) -> None:
        while True:
            for trigger, watchdog in self._watchdogs.items():
                overdue = watchdog.overdue()
                if overdue:
                    self._report(trigger, overdue)

            await asyncio.sleep(interval)

    def _report(self, trigger: WatchdogTrigger, overdue: list[Activity]) -> None:
        oldest = overdue[0]
        msg = f'`{trigger.value}` watchdog timeout! No activity in {int(time.time() - oldest.started_at)} seconds'
        if oldest.name:
            msg += f': {oldest.name}'
        if len(overdue) > 1:
            msg += f' (and {len(overdue) - 1} more)'

        action = self._actions[trigger]
        if action == WatchdogAction.ignore:
            _logger.debug('%s, ignoring', msg)
            return
        if action not in (WatchdogAction.warning, WatchdogAction.exception):
            raise NotImplementedError(f'Unsupported watchdog action: {action}')

        # NOTE: Show where the task is stuck once per activity, not on every check
        if oldest.task and not oldest.reported:
            msg += f'\n`{oldest.task.get_name()}` is awaiting:\n{format_task_stack(oldest.task)}'
            for watchdog in self._watchdogs.values():
                for activity in watchdog.activities():
                    if activity.task is oldest.task:
                        activity.reported = True

        if action == WatchdogAction.exception:
            raise WatchdogTimeoutError(msg)
        _logger.warning(msg)

    @contextmanager
    def watch(self, trigger: WatchdogTrigger, name: str) -> Iterator[None]:
        """Track an activity of the current task until the block exits"""
        watchdog = self._watchdogs.get(trigger)
        if watchdog is None:
            yield
            return

        activity = Activity(name, time.time(), asyncio.current_task())
        watchdog.start(activity, activity)
        outer = _current.get()
        _current.set((*outer, (trigger, activity)))
        try:
            yield
        finally:
            _current.set(outer)
            activity.finished = True
            watchdog.stop(activity)

    def _current_activities(self, trigger: WatchdogTrigger) -> list[Activity]:
        """Activities watched in the current context, including finished ones a spawned task has outlived"""
        return [activity for t, activity in _current.get() if t == trigger]

    def heartbeat(self, trigger: WatchdogTrigger, name: str = '') -> None:
        """Restart the countdown for `name`.

        Without a name, restart the countdown of the callbacks or transactions being watched in the current context;
        outside of them, the trigger has a single countdown.
        """
        watchdog = self._watchdogs.get(trigger)
        if watchdog is None:
            return
        if not name and (current := self._current_activities(trigger)):
            for activity in current:
                if not activity.finished:
                    activity.started_at, activity.reported = time.time(), False
                    watchdog.start(activity, activity)
            return
        watchdog.start(name, Activity(name, time.time()))

    def reset(self, trigger: WatchdogTrigger, name: str = '') -> None:
        """Stop the countdown for `name`; without a name, also stop watching the current callbacks or transactions"""
        watchdog = self._watchdogs.get(trigger)
        if watchdog is None:
            return
        if not name:
            for activity in self._current_activities(trigger):
                watchdog.stop(activity)
        watchdog.stop(name)


# NOTE: Use this singleton from everywhere
watchdog = WatchdogManager()
