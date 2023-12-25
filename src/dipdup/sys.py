import asyncio
import logging
import signal
import sys
import warnings
from collections import deque
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from dipdup import env

_is_shutting_down = False
_futures: deque[asyncio.Future[None]] = deque()


async def _shutdown() -> None:  # pragma: no cover
    global _is_shutting_down
    if _is_shutting_down:
        return
    _is_shutting_down = True

    # NOTE: Prevents BrokenPipeError when piping output to another process
    # sys.stderr.close()

    tasks = filter(lambda t: t != asyncio.current_task(), asyncio.all_tasks())
    list(map(asyncio.Task.cancel, tasks))
    await asyncio.gather(*tasks, return_exceptions=True)


def is_shutting_down() -> bool:
    return _is_shutting_down


def set_up_logging() -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(levelname)-8s %(name)-20s %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # NOTE: Nothing useful there
    logging.getLogger('tortoise').setLevel(logging.WARNING)

    if env.DEBUG:
        logging.getLogger('dipdup').setLevel(logging.DEBUG)


def fire_and_forget(aw: Awaitable[Any]) -> None:
    """Fire and forget coroutine"""
    future = asyncio.ensure_future(aw)
    _futures.append(future)
    future.add_done_callback(lambda _: _futures.remove(future))


def set_up_process(signals: bool) -> None:
    """Set up interpreter process-wide state"""
    # NOTE: Skip for integration tests
    if env.TEST:
        return

    # NOTE: Register shutdown handler for non-interactive commands (avoiding conflicts with Click prompts)
    if signals:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            signal.SIGINT,
            lambda: asyncio.ensure_future(_shutdown()),
        )

    # NOTE: Better discoverability of DipDup packages and configs
    sys.path.append(str(Path.cwd()))
    sys.path.append(str(Path.cwd() / 'src'))
    sys.path.append(str(Path.cwd() / '..'))

    # NOTE: Format warnings as normal log messages
    logging.captureWarnings(True)
    warnings.formatwarning = lambda msg, *a, **kw: str(msg)
