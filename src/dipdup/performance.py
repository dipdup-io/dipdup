"""This module contains code to manage queues, caches and tune metrics.

There are three module-level singletons, one for each type of resource:

- `_QueueManager` for simple deque queues
- `_CacheManager` for LRU caches
- `_MetricManager` for performance metrics and pprofile integration

These three need to be importable from anywhere, so no internal imports in this module. Prometheus is not there yet.
"""

import gc
import logging
import time
from collections import deque
from collections.abc import Callable
from collections.abc import Coroutine
from collections.abc import Generator
from contextlib import contextmanager
from functools import _CacheInfo
from functools import lru_cache
from itertools import chain
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from async_lru import alru_cache
from pydantic.dataclasses import dataclass

from dipdup.exceptions import FrameworkException
from dipdup.prometheus import Counter
from dipdup.prometheus import Gauge
from dipdup.prometheus import Histogram

if TYPE_CHECKING:

    from dipdup.models import CachedModel

_logger = logging.getLogger(__name__)


class _CacheManager:
    def __init__(self) -> None:
        self._plain: dict[str, dict[Any, Any]] = {}
        self._lru: dict[str, Callable[..., Any]] = {}
        self._alru: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}
        self._models: set[type[CachedModel]] = set()

    def add_plain(
        self,
        obj: dict[Any, Any],
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
        if cls in self._models:
            raise FrameworkException(f'Model cache for `{cls}` already exists')
        self._models.add(cls)

    def stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for name, plain_cache in self._plain.items():
            name = f'plain:{name}'
            stats[name] = {'size': len(plain_cache)}
        for name, fn_cache in chain(self._lru.items(), self._alru.items()):
            name = f'lru:{name}'
            c = cast(_CacheInfo, fn_cache.cache_info())  # type: ignore[attr-defined]
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
        for model_cls in self._models:
            name = f'model:{model_cls.__name__}'
            stats[name] = model_cls.stats()

        return stats

    def clear(self) -> None:
        items = 0

        for plain_cache in self._plain.values():
            items += len(plain_cache)
            plain_cache.clear()
        for fn_cache in chain(self._lru.values(), self._alru.values()):
            stats = cast(_CacheInfo, fn_cache.cache_info())  # type: ignore[attr-defined]
            items += stats.currsize
            fn_cache.cache_clear()  # type: ignore[attr-defined]
        for model_cls in self._models:
            items += model_cls.stats()['size']
            model_cls.clear()

        _logger.debug('Cleared %d cached items', items)

        collected = gc.collect()
        _logger.debug('Garbage collected %d items', collected)


class _QueueManager:
    def __init__(self) -> None:
        self._queues: dict[str, deque[Any]] = {}
        self._limits: dict[str, int] = {}

    def add_queue(
        self,
        queue: deque[Any],
        name: str,
        limit: int = 0,
    ) -> None:
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


@dataclass
class _MetricManager:
    # Copied from prometheus.py, probably should be removed
    enabled: bool = False

    # NOTE: General metrics
    # NOTE: Transformed to prometheus metrics easily
    levels_indexed = Counter('dipdup_levels_indexed_total', 'Total number of levels indexed')
    levels_nonempty = Counter('dipdup_levels_nonempty_total', 'Total number of nonempty levels indexed')
    levels_total = Counter('dipdup_levels_total', 'Total number of levels')
    objects_indexed = Counter('dipdup_objects_indexed_total', 'Total number of objects indexed')

    # NOTE: Orignally in prometheus.py
    indexes_total = Counter(
        'dipdup_indexes_total',
        'Number of indexes in operation by status',
        ('status',),
    )
    levels_to_sync = Histogram(
        'dipdup_index_levels_to_sync_total',
        'Number of levels to reach synced state',
        ['index'],
    )
    levels_to_realtime = Histogram(
        'dipdup_index_levels_to_realtime_total',
        'Number of levels to reach realtime state',
        ['index'],
    )
    # FIXME: move inside _MetricManager
    _index_total_sync_duration = Histogram(
        'dipdup_index_total_sync_duration_seconds',
        'Duration of the last index syncronization',
    )
    _index_total_realtime_duration = Histogram(
        'dipdup_index_total_realtime_duration_seconds',
        'Duration of the last index realtime syncronization',
    )

    _datasource_head_updated = Histogram(
        'dipdup_datasource_head_updated_timestamp',
        'Timestamp of the last head update',
        ['datasource'],
    )
    _datasource_rollbacks = Counter(
        'dipdup_datasource_rollbacks_total',
        'Number of rollbacks',
        ['datasource'],
    )

    _http_errors = Counter(
        'dipdup_http_errors_total',
        'Number of http errors',
        ['url', 'status'],
    )
    _http_errors_in_row = Histogram(
        'dipdup_http_errors_in_row',
        'Number of consecutive failed requests',
    )

    _sqd_processor_last_block = Gauge(
        'sqd_processor_last_block',
        'Level of the last processed block from Subsquid Network',
    )
    _sqd_processor_chain_height = Gauge(
        'sqd_processor_chain_height',
        'Current chain height as reported by Subsquid Network',
    )
    _sqd_processor_archive_http_errors_in_row = Histogram(
        'sqd_processor_archive_http_errors_in_row',
        'Number of consecutive failed requests to Subsquid Network',
    )

    # NOTE: Index metrics
    # NOTE: Merged with the one in prometheus.py
    handlers_matched = Gauge('dipdup_index_handlers_matched_total', 'Index total hits', ['handler'])
    time_in_matcher = Histogram('dipdup_index_time_in_matcher_seconds', 'Time spent in matcher', ['index'])
    time_in_callbacks = Histogram('dipdup_index_time_in_callbacks_seconds', 'Time spent in callbacks', ['index'])

    # NOTE: Datasource metrics
    time_in_requests = Histogram(
        'dipdup_datasource_time_in_requests_seconds', 'Time spent in datasource requests', ['datasource']
    )
    requests_total = Counter('dipdup_datasource_requests_total', 'Total number of datasource requests', ['datasource'])

    # NOTE: Various timestamps
    started_at: float = 0.0
    synchronized_at: float = 0.0
    realtime_at: float = 0.0
    metrics_updated_at: float = 0.0

    # NOTE: Speed estimates
    levels_speed: float = 0.0
    levels_speed_average: float = 0.0
    levels_nonempty_speed: float = 0.0
    objects_speed: float = 0.0

    # NOTE: Time estimates
    time_passed: float = 0.0
    time_left: float = 0.0
    progress: float = 0.0

    @contextmanager
    def measure_total_sync_duration(self) -> Generator[None, None, None]:
        with self._index_total_sync_duration.time():
            yield

    @contextmanager
    def measure_total_realtime_duration(self) -> Generator[None, None, None]:
        with self._index_total_realtime_duration.time():
            yield

    def set_datasource_head_updated(self, name: str) -> None:
        self._datasource_head_updated.labels(datasource=name).observe(time.time())

    def set_datasource_rollback(self, name: str) -> None:
        self._datasource_rollbacks.labels(datasource=name).inc()

    def set_http_error(self, url: str, status: int) -> None:
        self._http_errors.labels(url=url, status=status).inc()

    def set_sqd_processor_last_block(self, last_block: int) -> None:
        self._sqd_processor_last_block.set(last_block)

    def set_sqd_processor_chain_height(self, chain_height: int) -> None:
        self._sqd_processor_chain_height.set(chain_height)

    def set_http_errors_in_row(self, url: str, errors_count: int) -> None:
        self._http_errors_in_row.observe(errors_count)
        if 'subsquid' in url:
            self._sqd_processor_archive_http_errors_in_row.observe(errors_count)

    def stats(self) -> dict[str, Any]:
        def _round(value: Any) -> Any:
            if isinstance(value, Counter | Gauge | Histogram):
                return _round(value.value)
            if isinstance(value, dict):
                return {k: _round(v) for k, v in value.items()}
            if isinstance(value, float):
                return round(value, 2)
            return value

        return {k: _round(v) for k, v in self.__dict__.items() if not k.startswith('_')}


caches = _CacheManager()
queues = _QueueManager()
metrics = _MetricManager()


def get_stats() -> dict[str, Any]:
    return {
        'caches': caches.stats(),
        'queues': queues.stats(),
        'metrics': metrics.stats(),
    }
