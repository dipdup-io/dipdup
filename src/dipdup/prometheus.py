import time
from collections import deque
from contextlib import contextmanager
from typing import Deque
from typing import Dict

from prometheus_client import Gauge  # type: ignore

level_sync_durations: Deque[float] = deque(maxlen=100)
level_realtime_durations: Deque[float] = deque(maxlen=100)
total_sync_durations: Deque[float] = deque(maxlen=100)
total_realtime_durations: Deque[float] = deque(maxlen=100)
levels_to_sync: Dict[str, int] = dict()
levels_to_realtime: Dict[str, int] = dict()


@contextmanager
def averaged_duration(queue: deque):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    queue.appendleft(end - start)


indexes_total = Gauge('dipdup_indexes_total', 'Total number of indexes')
indexes_synced = Gauge('dipdup_indexes_synced', 'Number of synchronized indexes')
indexes_realtime = Gauge('dipdup_indexes_realtime', 'Number of realtime indexes')

index_level_sync_duration = Gauge('dipdup_index_level_sync_duration', 'Duration of indexing a single level', ['field'])
index_level_realtime_duration = Gauge('dipdup_index_level_realtime_duration', 'Duration of last index syncronization', ['field'])

index_total_sync_duration = Gauge('dipdup_index_total_sync_duration', 'Duration of the last index syncronization', ['field'])
index_total_realtime_duration = Gauge(
    'dipdup_index_total_realtime_duration', 'Duration of the last index realtime syncronization', ['field']
)

index_levels_to_sync = Gauge('dipdup_index_levels_to_sync', 'Number of levels to reach synced state')
index_levels_to_realtime = Gauge('dipdup_index_levels_to_realtime', 'Number of levels to reach realtime state')

datasource_head_updated = Gauge('dipdup_datasource_head_updated', 'Timestamp of the last head update', ['datasource'])
callback_duration = Gauge('dipdup_callback_duration', 'Duration of callback execution', ['callback'])


def refresh():
    if level_sync_durations:
        index_level_sync_duration.labels(field='min').set(min(level_sync_durations))
        index_level_sync_duration.labels(field='max').set(max(level_sync_durations))
        index_level_sync_duration.labels(field='avg').set(sum(level_sync_durations) / len(level_sync_durations))

    if level_realtime_durations:
        index_level_realtime_duration.labels(field='min').set(min(level_realtime_durations))
        index_level_realtime_duration.labels(field='max').set(max(level_realtime_durations))
        index_level_realtime_duration.labels(field='avg').set(sum(level_realtime_durations) / len(level_realtime_durations))

    if total_sync_durations:
        index_total_sync_duration.labels(field='min').set(min(total_sync_durations))
        index_total_sync_duration.labels(field='max').set(max(total_sync_durations))
        index_total_sync_duration.labels(field='avg').set(sum(total_sync_durations) / len(total_sync_durations))

    if total_realtime_durations:
        index_total_realtime_duration.labels(field='min').set(min(total_realtime_durations))
        index_total_realtime_duration.labels(field='max').set(max(total_realtime_durations))
        index_total_realtime_duration.labels(field='avg').set(sum(total_realtime_durations) / len(total_realtime_durations))

    index_levels_to_sync.set(sum(levels_to_sync.values()))
    index_levels_to_realtime.set(sum(levels_to_realtime.values()))
