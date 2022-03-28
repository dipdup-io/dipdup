# `advanced`

```yaml
advanced:
  early_realtime: False
  merge_subscriptions: False
  postpone_jobs: False
  reindex:
    manual: wipe
    migration: exception
    rollback: ignore
    config_modified: exception
    schema_modified: exception
```

This config section allows users to tune some system-wide options, either experimental or unsuitable for generic configurations.

| field | description |
| - | - |
| `reindex` | Mapping of reindexing reasons and actions DipDup performs |
| `scheduler` | `apscheduler` scheduler config |
| `postpone_jobs` | Do not start job scheduler until all indexes are in realtime state |
| `early_realtime` | Establish realtime connection immediately after startup |
| `merge_subscriptions` | Subscribe to all operations instead of exact channels |
| `metadata_interface` | Expose metadata interface for TzKT |

See [5.4. Feature flags](../advanced/performance/flags.md) for details.

See [5.3. Reindexing](../advanced/reindexing.md) for details.

CLI flags have priority over self-titled `AdvancedConfig` fields.
