import time
from collections import deque
from contextlib import contextmanager
from typing import Deque
from typing import Dict

from prometheus_client import Gauge  # type: ignore

_levels_to_sync: Dict[str, int] = dict()
_levels_to_realtime: Dict[str, int] = dict()

_indexes_total = Gauge('dipdup_indexes_total', 'Total number of indexes')
_indexes_synced = Gauge('dipdup_indexes_synced', 'Number of synchronized indexes')
_indexes_realtime = Gauge('dipdup_indexes_realtime', 'Number of realtime indexes')

_index_level_sync_duration = Gauge('dipdup_index_level_sync_duration', 'Duration of indexing a single level', ['field'])
_index_level_realtime_duration = Gauge('dipdup_index_level_realtime_duration', 'Duration of last index syncronization', ['field'])
_index_total_sync_duration = Gauge('dipdup_index_total_sync_duration', 'Duration of the last index syncronization', ['field'])
_index_total_realtime_duration = Gauge(
    'dipdup_index_total_realtime_duration', 'Duration of the last index realtime syncronization', ['field']
)
_index_levels_to_sync = Gauge('dipdup_index_levels_to_sync', 'Number of levels to reach synced state')
_index_levels_to_realtime = Gauge('dipdup_index_levels_to_realtime', 'Number of levels to reach realtime state')
_index_total_matches = Gauge('dipdup_index_total_matches', 'Index total hits')

_datasource_head_updated = Gauge('dipdup_datasource_head_updated', 'Timestamp of the last head update', ['datasource'])
_datasource_rollback_count = Gauge('dipdup_datasource_rollback_count', 'Number of rollbacks', ['datasource'])

_http_errors = Gauge('dipdup_http_errors', 'Number of http errors', ['url', 'status'])
_callback_duration = Gauge('dipdup_callback_duration', 'Duration of callback execution', ['callback'])


@contextmanager
def _average_duration(queue: deque):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    queue.appendleft(end - start)


def _update_average_metric(queue: deque, metric: Gauge) -> None:
    if not queue:
        return
    metric.labels(field='min').set(min(queue))
    metric.labels(field='max').set(max(queue))
    metric.labels(field='avg').set(sum(queue) / len(queue))


class Metrics:
    enabled = False
    _level_sync_durations: Deque[float] = deque(maxlen=100)
    _level_realtime_durations: Deque[float] = deque(maxlen=100)
    _total_sync_durations: Deque[float] = deque(maxlen=100)
    _total_realtime_durations: Deque[float] = deque(maxlen=100)

    def __new__(cls):
        raise TypeError('Metrics is a singleton')

    @classmethod
    def refresh(cls) -> None:
        _update_average_metric(cls._level_sync_durations, _index_level_sync_duration)
        _update_average_metric(cls._level_realtime_durations, _index_level_realtime_duration)
        _update_average_metric(cls._total_sync_durations, _index_total_sync_duration)
        _update_average_metric(cls._total_realtime_durations, _index_total_realtime_duration)
        _index_levels_to_sync.set(sum(_levels_to_sync.values()))
        _index_levels_to_realtime.set(sum(_levels_to_realtime.values()))

    @classmethod
    @contextmanager
    def measure_level_sync_duration(cls):
        with _average_duration(cls._level_sync_durations):
            yield

    @classmethod
    @contextmanager
    def measure_level_realtime_duration(cls):
        with _average_duration(cls._level_realtime_durations):
            yield

    @classmethod
    @contextmanager
    def measure_total_sync_duration(cls):
        with _average_duration(cls._total_sync_durations):
            yield

    @classmethod
    @contextmanager
    def measure_total_realtime_duration(cls):
        with _average_duration(cls._total_realtime_durations):
            yield

    @classmethod
    @contextmanager
    def measure_callback_duration(cls, name: str):
        with _callback_duration.labels(callback=name).time():
            yield

    @classmethod
    def set_indexes_count(cls, total: int, synced: int, realtime: int) -> None:
        _indexes_total.set(total)
        _indexes_synced.set(synced)
        _indexes_realtime.set(realtime)

    @classmethod
    def set_datasource_head_updated(cls, name: str):
        _datasource_head_updated.labels(datasource=name).set(time.time())

    @classmethod
    def set_datasource_rollback(cls, name: str):
        _datasource_rollback_count.labels(datasource=name).inc()

    @classmethod
    def set_http_error(cls, url: str, status: int) -> None:
        _http_errors.labels(url=url, status=status).inc()

    @classmethod
    def set_index_total_matches(cls, amount: float) -> None:
        _index_total_matches.inc(amount)

    @classmethod
    def set_levels_to_sync(cls, index: str, level: int):
        _levels_to_sync[index] = level

    @classmethod
    def set_levels_to_realtime(cls, index: str, level: int):
        _levels_to_realtime[index] = level

    @classmethod
    def apply_sample_size(cls, sample_size: int) -> None:
        cls._level_sync_durations = deque(maxlen=sample_size)
        cls._level_realtime_durations = deque(maxlen=sample_size)
        cls._total_sync_durations = deque(maxlen=sample_size)
        cls._total_realtime_durations = deque(maxlen=sample_size)
