from collections import deque
from functools import _CacheInfo
from functools import lru_cache
from typing import Any
from typing import Callable
from typing import cast


class CacheManager:
    def __init__(self) -> None:
        self._status = 'idle'
        self._cached_fn: dict[Callable[..., Any], Callable[..., Any]] = {}
        self._queues: dict[str, deque[Any]] = {}

    def lru_cache(self, fn: Callable[..., Any], maxsize: int = 128) -> Callable[..., Any]:
        if fn in self._cached_fn:
            return self._cached_fn[fn]
        else:
            self._cached_fn[fn] = lru_cache(maxsize)(fn)
            return self._cached_fn[fn]

    def stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {
            'status': self._status,
            'caches': {},
            'queues': {},
        }
        for fn, cached_fn in self._cached_fn.items():
            c = cast(_CacheInfo, cached_fn.cache_info())  # type: ignore[attr-defined]
            if not c.hits and not c.misses:
                continue
            stats['caches'][fn.__name__] = {
                'full': (c.currsize / c.maxsize * 100) if c.maxsize else 0,
                'hit_rate': c.hits / (c.hits + c.misses) * 100,
            }

        for name, queue in self._queues.items():
            stats['queues'][name] = {
                'size': len(queue),
                'full': len(queue) / (queue.maxlen) * 100 if queue.maxlen else 0,
            }
        return stats

    def add_queue(self, name: str, queue: deque[Any]) -> None:
        self._queues[name] = queue

    def status(self, status: str) -> None:
        self._status = status


cache = CacheManager()
