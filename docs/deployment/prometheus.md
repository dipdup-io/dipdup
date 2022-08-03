# Prometheus integration

DipDup provides basic integration with the Prometheus monitoring system by exposing some metrics.

When running DipDup in Docker make sure that the Prometheus instance is in the same network.

## Available metrics

The following metrics are exposed under `dipdup` namespace:

| metric name | description |
|-|-|
| `dipdup_indexes_total` | Number of indexes in operation by status |
| `dipdup_index_level_sync_duration_seconds` | Duration of indexing a single level |
| `dipdup_index_level_realtime_duration_seconds` | Duration of last index syncronization |
| `dipdup_index_total_sync_duration_seconds` | Duration of the last index syncronization |
| `dipdup_index_total_realtime_duration_seconds` | Duration of the last index realtime syncronization |
| `dipdup_index_levels_to_sync_total` | Number of levels to reach synced state |
| `dipdup_index_levels_to_realtime_total` | Number of levels to reach realtime state |
| `dipdup_index_handlers_matched_total` | Index total hits |
| `dipdup_datasource_head_updated_timestamp` | Timestamp of the last head update |
| `dipdup_datasource_rollbacks_total` | Number of rollbacks |
| `dipdup_http_errors_total` | Number of http errors |
| `dipdup_callback_duration_seconds` | Duration of callback execution |

You can also query {{ #summary advanced/internal-models.md}} for monitoring purposes.
