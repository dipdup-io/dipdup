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

This config section allows users to tune some system-wide options. Those are either experimental or just not suitable for generic configurations.

|field|description|
|-|-|
|`early_realtime`<br>`merge_subscriptions`<br>`postpone_jobs` |Another way to set [`run` command](../cli-reference/run.md) flags. Useful for maintaining per-deployment configurations. |
|`reindex`|Configure action on reindexing triggered. See [this paragraph](#configurable-action-on-reindex) for details.|

CLI flags have priority over self-titled `AdvancedConfig` fields.
