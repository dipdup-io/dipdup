import asyncio
import logging
import sys
import warnings
from collections import deque
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from dipdup import env

_futures: deque[asyncio.Future[None]] = deque()


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


def set_up_process() -> None:
    """Set up interpreter process-wide state"""
    # NOTE: Skip for integration tests
    if env.TEST:
        return

    # NOTE: Better discoverability of DipDup packages and configs
    sys.path.append(str(Path.cwd()))
    sys.path.append(str(Path.cwd() / 'src'))
    sys.path.append(str(Path.cwd() / '..'))

    # NOTE: Format warnings as normal log messages
    logging.captureWarnings(True)
    warnings.formatwarning = lambda msg, *a, **kw: str(msg)
