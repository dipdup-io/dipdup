import logging
import time
from collections import defaultdict
from collections import deque
from contextlib import contextmanager
from enum import Enum
from functools import _CacheInfo
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterator
from typing import cast

_logger = logging.getLogger(__name__)


class PerformanceStats:
    ...


class CacheManager:
    def __init__(self) -> None:
        self._lru_caches: dict[str, Callable[..., Any]] = {}

    def lru_cache(self, fn: Callable[..., Any], maxsize: int, name: str | None = None) -> Callable[..., Any]:
        if name is None:
            name = f'{fn.__module__}.{fn.__name__}:{id(fn)}'
        if name in self._lru_caches:
            raise Exception(f'LRU cache `{name}` already exists')
        self._lru_caches[name] = lru_cache(maxsize)(fn)
        return self._lru_caches[name]

    def stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for name, cached_fn in self._lru_caches.items():
            c = cast(_CacheInfo, cached_fn.cache_info())  # type: ignore[attr-defined]
            if not c.hits and not c.misses:
                continue
            stats[name] = {
                'full': (c.currsize / c.maxsize) if c.maxsize else 0,
                'hit_rate': c.hits / (c.hits + c.misses),
            }

        return stats


class QueueManager:
    def __init__(self) -> None:
        self._queues: dict[str, deque[Any]] = {}

    def add_queue(self, queue: deque[Any], name: str | None = None) -> None:
        if name is None:
            name = f'{queue.__module__}:{id(queue)}'
        if name in self._queues:
            raise Exception(f'Queue `{name}` already exists')
        self._queues[name] = queue

    def stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for name, queue in self._queues.items():
            stats[name] = {
                'size': len(queue),
                'full': len(queue) / (queue.maxlen) if queue.maxlen else 0,
            }
        return stats


class ProfilerLevel(Enum):
    off = 'off'
    basic = 'basic'
    full = 'full'


class Profiler:
    """Usage:

    profiler.basic and profiler.increase('time_handlers', 0.1)
    profiler.full and stack.enter_context(profiler.enter_context('filename_in_cwd'))

    """

    def __init__(self) -> None:
        self._level = ProfilerLevel.off
        self._stats: defaultdict[str, float] = defaultdict(float)

    @property
    def basic(self) -> bool:
        return self._level == ProfilerLevel.basic

    @property
    def full(self) -> bool:
        return self._level == ProfilerLevel.full

    def set_level(self, level: ProfilerLevel) -> None:
        self._level = level

    def set(self, name: str, value: float) -> None:
        self._stats[name] = value

    def inc(self, name: str, value: float) -> None:
        self._stats[name] = self._stats.get(name, 0) + value

    @contextmanager
    def enter_context(self, name: str) -> Iterator[None]:
        try:
            import pprofile  # type: ignore[import]
        except ImportError:
            _logger.error('pprofile not installed, falling back to basic profiling')
            self._level = ProfilerLevel.basic
            return

        profiler = pprofile.Profile()
        with profiler():
            yield

        profiler.dump_stats(Path.cwd() / f'cachegrind.out.dipdup.{name}.{round(time.time())}')

    def stats(self) -> dict[str, float]:
        return self._stats


caches = CacheManager()
queues = QueueManager()
profiler = Profiler()
