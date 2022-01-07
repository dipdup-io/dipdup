from prometheus_client import Gauge  # type: ignore

indexes_total = Gauge('dipdip_indexes_total', 'Total number of indexes')
indexes_synchronized = Gauge('dipdip_indexes_synchronized', 'Number of synchronized indexes')
indexes_realtime = Gauge('dipdip_indexes_realtime', 'Number of realtime indexes')

index_level_duration = Gauge('dipdup_index_level_duration', 'Duration of indexing a single level', ['index'])
index_sync_duration = Gauge('dipdup_index_sync_duration', 'Duration of last index syncronization', ['index'])
index_queue_size = Gauge('dipdup_index_queue_size', 'Size of index realtime queue', ['index'])

datasource_head_updated = Gauge('dipdup_datasource_head_updated', 'Timestamp of the last head update', ['datasource'])
callback_duration = Gauge('dipdup_callback_duration', 'Duration of callback execution', ['callback'])
