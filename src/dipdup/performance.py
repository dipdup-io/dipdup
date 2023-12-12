"""This module contains code to manage queues, caches and tune metrics.

There are three module-level singletons, one for each type of resource:

- `_QueueManager` for simple deque queues
- `_CacheManager` for LRU caches
- `_MetricManager` for performance metrics and pprofile integration

These three need to be importable from anywhere, so no internal imports in this module. Prometheus is not there yet.
"""

import logging
from collections import defaultdict
from collections import deque
from collections.abc import Callable
from collections.abc import Coroutine
from collections.abc import Sized
from functools import _CacheInfo
from functools import lru_cache
from itertools import chain
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from async_lru import alru_cache
from lru import LRU

from dipdup.exceptions import FrameworkException

if TYPE_CHECKING:
    from tortoise.models import Model

    from dipdup.models import CachedModel

_logger = logging.getLogger(__name__)


class _CacheManager:
    def __init__(self) -> None:
        self._plain: dict[str, Sized] = {}
        self._lru: dict[str, Callable[..., Any]] = {}
        self._alru: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}
        self._model: dict[str, dict[int | str, Model]] = {}

    def add_plain(
        self,
        obj: Sized,
        name: str,
    ) -> None:
        self._plain[name] = obj

    def add_lru(
        self,
        fn: Callable[..., Any],
        maxsize: int | None,
        name: str | None = None,
    ) -> Callable[..., Any]:
        if name is None:
            name = f'{fn.__module__}.{fn.__name__}:{id(fn)}'
        if name in self._lru or name in self._alru:
            raise FrameworkException(f'LRU cache `{name}` already exists')

        self._lru[name] = lru_cache(maxsize)(fn)
        return self._lru[name]

    def add_alru(
        self,
        fn: Callable[..., Coroutine[Any, Any, None]],
        maxsize: int,
        name: str | None = None,
    ) -> Callable[..., Coroutine[Any, Any, None]]:
        if name is None:
            name = f'{fn.__module__}.{fn.__name__}:{id(fn)}'
        if name in self._lru or name in self._alru:
            raise FrameworkException(f'LRU cache `{name}` already exists')

        self._alru[name] = alru_cache(maxsize)(fn)
        return self._alru[name]

    def add_model(
        self,
        cls: 'type[CachedModel]',
    ) -> None:
        if cls.__name__ in self._model:
            raise Exception(f'Model cache for `{cls}` already exists')

        try:
            maxsize = cls.Meta.maxsize  # type: ignore[attr-defined]
            self._model[cls.__name__] = LRU(maxsize)  # type: ignore[assignment]
        except AttributeError:
            self._model[cls.__name__] = {}

    def stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for name, cache in self._plain.items():
            name = f'plain:{name}'
            stats[name] = {'size': len(cache)}
        for name, cached_fn in chain(self._lru.items(), self._alru.items()):
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
        for name, cache in self._model.items():
            name = f'model:{name}'
            stats[name] = {
                'size': len(cache),
            }

        return stats


class _QueueManager:
    def __init__(self) -> None:
        self._queues: dict[str, deque[Any]] = {}
        self._limits: dict[str, int] = {}

    def add_queue(self, queue: deque[Any], name: str | None = None, limit: int = 0) -> None:
        if name is None:
            name = f'{queue.__module__}:{id(queue)}'
        if name in self._queues:
            raise FrameworkException(f'Queue `{name}` already exists')
        self._queues[name] = queue
        self._limits[name] = limit

    def remove_queue(self, name: str) -> None:
        if name not in self._queues:
            raise FrameworkException(f'Queue `{name}` does not exist')
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


class _MetricManager:
    """Usage:

    metrics and metrics.increase('metric', 0.1)
    metrics.full and metrics.set('verbose_metric', 0.2)
    stack.enter_context(metrics.enter_context('package'))
    """

    def __init__(self) -> None:
        self._stats: defaultdict[str, float] = defaultdict(float)

    def set(self, name: str, value: float) -> bool:
        self._stats[name] = value
        return True

    def inc(self, name: str, value: float) -> bool:
        self._stats[name] += value
        return True

    def stats(self) -> dict[str, float]:
        return self._stats


caches = _CacheManager()
queues = _QueueManager()
metrics = _MetricManager()


def get_stats() -> dict[str, Any]:
    return {
        'caches': caches.stats(),
        'queues': queues.stats(),
        'metrics': metrics.stats(),
    }
