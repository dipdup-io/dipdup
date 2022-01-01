from prometheus_client import Gauge

active_indexes = Gauge('dipdip_active_indexes_total', 'Active indexes')
datasource_head_updated = Gauge('dipdup_datasource_head_updated_timestamp', 'Timestamp of the last head update', ['datasource'])