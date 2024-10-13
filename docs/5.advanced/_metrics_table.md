<!-- markdownlint-disable first-line-h1 -->
| name | description | type |
|-|-|-|
| dipdup_datasource_head_updated_timestamp | Timestamp of the last head update | Gauge |
| dipdup_datasource_requests | Total number of datasource requests | Counter |
| dipdup_datasource_rollbacks | Number of rollbacks | Counter |
| dipdup_datasource_time_in_requests_seconds | Time spent in datasource requests | Histogram |
| dipdup_http_errors | Number of http errors | Counter |
| dipdup_http_errors_in_row | Number of consecutive failed requests | Gauge |
| dipdup_index_handlers_matched | Index total hits | Counter |
| dipdup_index_levels_to_realtime_total | Number of levels to reach realtime state | Histogram |
| dipdup_index_levels_to_sync_total | Number of levels to reach synced state | Histogram |
| dipdup_index_time_in_callbacks_seconds | Time spent in callbacks | Histogram |
| dipdup_index_time_in_matcher_seconds | Time spent in matcher | Histogram |
| dipdup_index_total_realtime_duration_seconds | Duration of the last index realtime syncronization | Histogram |
| dipdup_index_total_sync_duration_seconds | Duration of the last index syncronization | Histogram |
| dipdup_indexes_total | Number of indexes in operation by status | Gauge |
| dipdup_levels_indexed_total | Total number of levels indexed | Gauge |
| dipdup_levels_nonempty | Total number of nonempty levels indexed | Counter |
| dipdup_levels_nonempty_speed | Nonempty levels per second | Gauge |
| dipdup_levels_speed | Levels per second | Gauge |
| dipdup_levels_speed_average | Average levels per second | Gauge |
| dipdup_levels_total | Total number of levels | Gauge |
| dipdup_metrics_updated_at_timestamp | Timestamp of the last metrics update | Gauge |
| dipdup_objects_indexed | Total number of objects indexed | Counter |
| dipdup_objects_speed | Objects per second | Gauge |
| dipdup_progress | Progress in percents | Gauge |
| dipdup_realtime_at_timestamp | Timestamp of the last realtime update | Gauge |
| dipdup_started_at_timestamp | Timestamp of the DipDup start | Gauge |
| dipdup_synchronized_at_timestamp | Timestamp of the last synchronization | Gauge |
| dipdup_time_left_seconds | Time left estimated until the end | Gauge |
| dipdup_time_passed_seconds | Time passed since the start | Gauge |
| sqd_processor_archive_http_errors_in_row | Number of consecutive failed requests to Subsquid Network | Gauge |
| sqd_processor_chain_height | Current chain height as reported by Subsquid Network | Gauge |
| sqd_processor_last_block | Level of the last processed block from Subsquid Network | Gauge |
