import time
from contextlib import contextmanager
from typing import Generator
from typing import NoReturn

from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram

_indexes_total = Gauge(
    'dipdup_indexes_total',
    'Number of indexes in operation by status',
    ('status',),
)

_index_level_sync_duration = Histogram(
    'dipdup_index_level_sync_duration_seconds',
    'Duration of indexing a single level',
)
_index_level_realtime_duration = Histogram(
    'dipdup_index_level_realtime_duration_seconds',
    'Duration of last index syncronization',
)
_index_total_sync_duration = Histogram(
    'dipdup_index_total_sync_duration_seconds',
    'Duration of the last index syncronization',
)
_index_total_realtime_duration = Histogram(
    'dipdup_index_total_realtime_duration_seconds',
    'Duration of the last index realtime syncronization',
)

_index_levels_to_sync = Histogram(
    'dipdup_index_levels_to_sync_total',
    'Number of levels to reach synced state',
    ['index'],
)
_index_levels_to_realtime = Histogram(
    'dipdup_index_levels_to_realtime_total',
    'Number of levels to reach realtime state',
    ['index'],
)
_index_handlers_matched = Gauge(
    'dipdup_index_handlers_matched_total',
    'Index total hits',
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
_callback_duration = Histogram(
    'dipdup_callback_duration_seconds',
    'Duration of callback execution',
    ['callback'],
)


class Metrics:
    enabled = False

    def __call__(cls) -> NoReturn:
        raise TypeError('Metrics is a singleton')

    @classmethod
    @contextmanager
    def measure_level_sync_duration(cls) -> Generator[None, None, None]:
        with _index_level_sync_duration.time():
            yield

    @classmethod
    @contextmanager
    def measure_level_realtime_duration(cls) -> Generator[None, None, None]:
        with _index_level_realtime_duration.time():
            yield

    @classmethod
    @contextmanager
    def measure_total_sync_duration(cls) -> Generator[None, None, None]:
        with _index_total_sync_duration.time():
            yield

    @classmethod
    @contextmanager
    def measure_total_realtime_duration(cls) -> Generator[None, None, None]:
        with _index_total_realtime_duration.time():
            yield

    @classmethod
    @contextmanager
    def measure_callback_duration(cls, name: str) -> Generator[None, None, None]:
        with _callback_duration.labels(callback=name).time():
            yield

    @classmethod
    def set_indexes_count(cls, active: int, synced: int, realtime: int) -> None:
        _indexes_total.labels(status='active').set(active)
        _indexes_total.labels(status='synced').set(synced)
        _indexes_total.labels(status='realtime').set(realtime)

    @classmethod
    def set_datasource_head_updated(cls, name: str) -> None:
        _datasource_head_updated.labels(datasource=name).observe(time.time())

    @classmethod
    def set_datasource_rollback(cls, name: str) -> None:
        _datasource_rollbacks.labels(datasource=name).inc()

    @classmethod
    def set_http_error(cls, url: str, status: int) -> None:
        _http_errors.labels(url=url, status=status).inc()

    @classmethod
    def set_index_handlers_matched(cls, amount: float) -> None:
        _index_handlers_matched.inc(amount)

    @classmethod
    def set_levels_to_sync(cls, index: str, levels: int) -> None:
        _index_levels_to_sync.labels(index=index).observe(levels)

    @classmethod
    def set_levels_to_realtime(cls, index: str, levels: int) -> None:
        _index_levels_to_realtime.labels(index=index).observe(levels)
