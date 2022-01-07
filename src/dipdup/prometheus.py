from prometheus_client import Gauge  # type: ignore

indexes_total = Gauge('dipdip_indexes_total', 'Active indexes')
indexes_synchronized = Gauge('dipdip_indexes_synchronized', 'Active indexes')
indexes_realtime = Gauge('dipdip_indexes_realtime', 'Active indexes')

datasource_head_updated = Gauge('dipdup_datasource_head_updated_timestamp', 'Timestamp of the last head update', ['datasource'])
callback_execution_duration = Gauge('dipdup_callback_execution_duration_seconds', 'Duration of callback execution', ['callback'])
level_indexing_duration = Gauge('dipdup_level_indexing_duration_seconds', 'Duration of indexing a single level', ['index'])
hook_execution_duration = Gauge('dipdup_hook_execution_duration_seconds', 'Duration of hook execution', ['hook'])
sync_duration = Gauge('dipdup_sync_duration_seconds', 'Duration of sync', ['index'])

index_realtime_queue_size = Gauge('dipdup_index_realtime_queue_size', 'Index realtime queue size', ['index'])
