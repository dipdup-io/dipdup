# Default hooks

Every DipDup project has multiple hooks called default; they fired on system-wide events and, like regular hooks, are not linked to any index. Names of those hooks are reserved; you can't use them in config.

## `on_rollback`

Fired when TzKT datasource has received a chain reorg message which can't be processed automatically.

If your indexer is stateless, you can just drop DB data saved after `to_level` and continue indexing or implement more complex logic. By default, this hook triggers full reindexing.

## `on_restart`

This hook executes right before starting indexing. It allows configuring DipDup in runtime based on data from external sources. Datasources are already initialized at the execution time and available at `ctx.datasources`. 

* Configure logging
* Add contracts and indexes


## `on_reindex`

This hook fires after the database is re-initialized after reindexing (wipe).

* Useful modify schema with arbitrary SQL.


## `on_synchronized`

This hook fires when every active index reaches a realtime state.

* Clear caches
* Update state somewhere


> 🤓 **SEE ALSO**
>
> * [5.3. Reindexing](../../advanced/reindexing.md)
> * [5.5. Executing SQL scripts](../sql.md)
> * [Handler context](../advanced/handler-context.md)