"""This module contains code to manage queues, caches and tune profiler.

There are three module-level singletons, one for each type of resource:

- `QueueManager` for simple deque queues
- `CacheManager` for LRU caches
- `ProfilerManager` for performance metrics and pprofile integration

These three need to be importable from anywhere, so no internal imports in this module. Prometheus is not there yet.
"""
import logging
import time
from collections import defaultdict
from collections import deque
from contextlib import asynccontextmanager
from enum import Enum
from functools import _CacheInfo
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import AsyncIterator
from typing import Callable
from typing import Sized
from typing import TypeVar
from typing import cast

from tortoise.models import Model

_logger = logging.getLogger(__name__)

_T = TypeVar('_T', bound=Model)
ModelCache = dict[int | str, Model]


class CacheManager:
    def __init__(self) -> None:
        self._plain_caches: dict[str, Sized] = {}
        self._lru_caches: dict[str, Callable[..., Any]] = {}
        self._model_caches: dict[str, ModelCache] = {}

    def plain_cache(
        self,
        obj: Sized,
        name: str,
    ) -> None:
        self._plain_caches[name] = obj

    def lru_cache(
        self,
        fn: Callable[..., Any],
        maxsize: int,
        name: str | None = None,
    ) -> Callable[..., Any]:
        if name is None:
            name = f'{fn.__module__}.{fn.__name__}:{id(fn)}'
        if name in self._lru_caches:
            raise Exception(f'LRU cache `{name}` already exists')
        self._lru_caches[name] = lru_cache(maxsize)(fn)
        return self._lru_caches[name]

    def model_cache(
        self,
        cls: type,
    ) -> None:
        if cls.__name__ in self._model_caches:
            raise Exception(f'Model cache for `{cls}` already exists')

        self._model_caches[cls.__name__] = {}

    def stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for name, cache in self._plain_caches.items():
            name = f'plain:{name}'
            stats[name] = {'size': len(cache)}
        for name, cached_fn in self._lru_caches.items():
            name = f'lru:{name}'
            c = cast(_CacheInfo, cached_fn.cache_info())  # type: ignore[attr-defined]
            if not c.hits and not c.misses:
                continue
            stats[name] = {
                'hits': c.hits,
                'misses': c.misses,
                'size': c.currsize,
                'limit': c.maxsize,
                'full': (c.currsize / c.maxsize) if c.maxsize else 0,
                'hit_rate': c.hits / (c.hits + c.misses),
            }
        for name, cache in self._model_caches.items():
            name = f'model:{name}'
            stats[name] = {
                'size': len(cache),
            }

        return stats


class QueueManager:
    def __init__(self) -> None:
        self._queues: dict[str, deque[Any]] = {}
        self._limits: dict[str, int] = {}

    def add_queue(self, queue: deque[Any], name: str | None = None, limit: int = 0) -> None:
        if name is None:
            name = f'{queue.__module__}:{id(queue)}'
        if name in self._queues:
            raise Exception(f'Queue `{name}` already exists')
        self._queues[name] = queue
        self._limits[name] = limit

    def remove_queue(self, name: str) -> None:
        if name not in self._queues:
            raise Exception(f'Queue `{name}` does not exist')
        del self._queues[name]
        del self._limits[name]

    def stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for name, queue in self._queues.items():
            size = len(queue)
            soft_limit = self._limits[name]
            if soft_limit:
                stats[name] = {
                    'size': size,
                    'limit': soft_limit,
                    'full': size / soft_limit,
                }
            elif queue.maxlen:
                stats[name] = {
                    'size': size,
                    'limit': queue.maxlen,
                    'full': size / queue.maxlen,
                }
            else:
                stats[name] = {
                    'size': size,
                    'limit': None,
                    'full': None,
                }
        return stats


class ProfilerLevel(Enum):
    off = 'off'
    basic = 'basic'
    full = 'full'


class Profiler:
    """Usage:

    profiler and profiler.increase('metric', 0.1)
    profiler.full and profiler.set('verbose_metric', 0.2)
    stack.enter_context(profiler.enter_context('package'))
    """

    def __init__(self) -> None:
        self._level = ProfilerLevel.off
        self._stats: defaultdict[str, float] = defaultdict(float)

    def __bool__(self) -> bool:
        return self._level != ProfilerLevel.off

    @property
    def basic(self) -> bool:
        return self._level != ProfilerLevel.off

    @property
    def full(self) -> bool:
        return self._level == ProfilerLevel.full

    @property
    def level(self) -> ProfilerLevel:
        return self._level

    def set_level(self, level: ProfilerLevel) -> None:
        self._level = level

    def set(self, name: str, value: float) -> bool:
        self._stats[name] = value
        return True

    def inc(self, name: str, value: float) -> bool:
        self._stats[name] += value
        return True

    def stats(self) -> dict[str, float]:
        return self._stats

    @asynccontextmanager
    async def with_pprofile(self, name: str) -> AsyncIterator[None]:
        try:
            import pprofile  # type: ignore[import]

            _logger.warning('Full profiling is enabled, this will affect performance')
        except ImportError:
            _logger.error('pprofile not installed, falling back to basic profiling')
            self._level = ProfilerLevel.basic
            return

        profiler = pprofile.Profile()
        with profiler():
            yield

        dump_path = Path.cwd() / f'cachegrind.out.dipdup.{name}.{round(time.time())}'
        _logger.info('Dumping profiling data to %s', dump_path)
        profiler.dump_stats(dump_path)


caches = CacheManager()
queues = QueueManager()
profiler = Profiler()


def get_stats() -> dict[str, Any]:
    return {
        'caches': caches.stats(),
        'queues': queues.stats(),
        'metrics': profiler.stats(),
    }