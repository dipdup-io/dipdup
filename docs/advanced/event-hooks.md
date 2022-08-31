# Event hooks

Every DipDup project has multiple event hooks (previously "default hooks"); they fire on system-wide events and, like regular hooks, are not linked to any index. Names of those hooks are reserved; you can't use them in config. It's also impossible to fire them manually or with a job scheduler.

## `on_restart`

This hook executes right before starting indexing. It allows configuring DipDup in runtime based on data from external sources. Datasources are already initialized at execution and available at `ctx.datasources`. You can, for example, configure logging here or add contracts and indexes in runtime instead of from static config.

## `on_reindex`

This hook fires after the database are re-initialized after reindexing (wipe). Helpful in modifying schema with arbitrary SQL scripts before indexing.

## `on_synchronized`

This hook fires when every active index reaches a realtime state. Here you can clear caches internal caches or do other cleanups.

## `on_index_rollback`

Fires when TzKT datasource has received a chain reorg message which can't be processed by dropping buffered messages (`buffer_size` option).

Since version 6.0 this hook performs a database-level rollback by default. If it doesn't work for you for some reason remove `ctx.rollback` call and implement your own rollback logic.

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/reindexing.md}}
> * {{ #summary advanced/sql.md}}
> * {{ #summary advanced/context.md}}
