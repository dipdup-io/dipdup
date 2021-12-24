# Reindexing

Several reasons trigger reindexing:

|reason|description|
|-|-|
|`manual`|Reindexing triggered manually from callback with `ctx.reindex`.|
|`migration`|Applied migration requires reindexing. Check release notes before switching between major DipDup versions to be prepared.|
|`rollback`|Reorg message received from TzKT can not be processed.|
|`config_modified`|One of the index configs has been modified.|
|`schema_modified`|Database schema has been modified. Try to avoid manual schema modifications in favor of [SQL hooks](../advanced/sql.md).|

Now it is possible to configure desirable action on reindexing triggered by the specific reason.

|action|description|
|-|-|
|`exception` (default)|Raise `ReindexingRequiredError` and quit with error code. The safest option since you can trigger reindexing accidentally, e.g., by a typo in config. Don't forget to set up the correct restart policy when using it with containers. |
|`wipe`|Drop the whole database and start indexing from scratch. Be careful with this option!|
|`ignore`|Ignore event and continue indexing as usual. It can lead to unexpected side-effects up to data corruption; make sure you know what you are doing.

To configure actions on each reason, add the following section to DipDup config:

```yaml
advanced:
  ...
  reindex:
    manual: wipe
    migration: exception
    rollback: ignore
    config_modified: exception
    schema_modified: exception
```
