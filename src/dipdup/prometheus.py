from prometheus_client import Gauge  # type: ignore

indexes_total = Gauge('dipdup_indexes_total', 'Total number of indexes')
indexes_synced = Gauge('dipdup_indexes_synced', 'Number of synchronized indexes')
indexes_realtime = Gauge('dipdup_indexes_realtime', 'Number of realtime indexes')

index_level_sync_duration = Gauge('dipdup_index_level_sync_duration', 'Duration of indexing a single level', ['index'])
index_level_realtime_duration = Gauge('dipdup_index_level_realtime_duration', 'Duration of last index syncronization', ['index'])

index_total_sync_duration = Gauge('dipdup_index_total_sync_duration', 'Duration of the last index syncronization', ['index'])
index_total_realtime_duration = Gauge(
    'dipdup_index_total_realtime_duration', 'Duration of the last index realtime syncronization', ['index']
)

index_levels_to_sync = Gauge('dipdup_index_levels_to_sync', 'Number of levels to reach synced state', ['index'])
index_levels_to_realtime = Gauge('dipdup_index_levels_to_realtime', 'Number of levels to reach realtime state', ['index'])

datasource_head_updated = Gauge('dipdup_datasource_head_updated', 'Timestamp of the last head update', ['datasource'])
callback_duration = Gauge('dipdup_callback_duration', 'Duration of callback execution', ['callback'])
