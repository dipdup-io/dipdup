# Common issues

## `MigrationRequiredError`

### Reason

DipDup was updated to release which `spec_version` differs from the value in the config file. You need to perform an automatic migration before starting indexing again.

### Solution

  1. Run [`dipdup migrate`](../cli/migrate.md) command.
  2. Review and commit changes.

## `ReindexingRequiredError`

### Reason

There can be several possible reasons that require reindexing from scratch:
* Your db models or your config (thus likely handler) changed, it means that all the previous data is probably not correct or will be inconsistent with the new one. Of course, you handle that manually or write a migration — luckily there is a way to disable reindexing for such cases.
* Also DipDup internal models or some raw indexing mechanisms changed (e.g. a serious bug was fixed) and unfortunetely it is required to re-run the indexer. Sometimes those changes do not affect your particular case and you also can skip the reindexing part.
* Finally there are chain reorgs happening from time to time, and if you don't have your `on_rollback` handler implemented — be ready for those errors. Luckily there is a generic approach to mitigate that — just wait for another block before appllying the previous one, i.e. introduce a lag into the indexing process.

### Solution

You can set how to react in each of the cases describe, here's the typical setup:

```yaml
advanced:
  reindex:
    manual: exception
    migration: exception
    rollback: exception
    config_modified: ignore
    schema_modified: ignore
```

In order to index with a lag add this TzKT datasource preference:

```yaml
datasources:
  tzkt_mainnet:
    kind: tzkt
    url: ${TZKT_URL:-https://api.tzkt.io}
    buffer_size: 1  # <--- one level reorgs are most common, 2-level reorgs are super rare
```