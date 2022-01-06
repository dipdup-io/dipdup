from prometheus_client import Gauge  # type: ignore

active_indexes = Gauge('dipdip_active_indexes_total', 'Active indexes')
datasource_head_updated = Gauge('dipdup_datasource_head_updated_timestamp', 'Timestamp of the last head update', ['datasource'])
callback_execution_duration = Gauge('dipdup_callback_execution_duration_seconds', 'Duration of callback execution', ['callback'])
