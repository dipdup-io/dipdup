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

|field|description|
|-|-|
|`early_realtime`<br>`merge_subscriptions`<br>`postpone_jobs` |Another way to set [`run` command](../cli-reference/run.md) flags. Useful for maintaining per-deployment configurations. See [5.4. Feature flags](../advanced/performance/flags.md) for details. |
|`reindex`|Configure action on reindexing triggered. See [5.3. Reindexing](../advanced/reindexing.md) for details.|

CLI flags have priority over self-titled `AdvancedConfig` fields.
