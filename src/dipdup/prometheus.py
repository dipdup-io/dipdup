from prometheus_client import Gauge  # type: ignore

indexes_total = Gauge('dipdip_indexes_total', 'Active indexes')
indexes_synchronized = Gauge('dipdip_indexes_synchronized', 'Active indexes')
indexes_realtime = Gauge('dipdip_indexes_realtime', 'Active indexes')

index_level_duration = Gauge('dipdup_index_level_duration', 'Duration of indexing a single level', ['index'])
index_sync_duration = Gauge('dipdup_index_sync_duration', 'Duration of sync', ['index'])
index_queue_size = Gauge('dipdup_index_queue_size', 'Index realtime queue size', ['index'])

datasource_head_updated = Gauge('dipdup_datasource_head_updated_timestamp', 'Timestamp of the last head update', ['datasource'])
callback_duration = Gauge('dipdup_callback_duration', 'Duration of callback execution', ['callback'])
