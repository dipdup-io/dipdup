# Hooks

### Default hooks

There is a special handlers DipDup generates for all indexes. They covers network events and initialization hooks. Names of those handlers are reserved, you can't use them in config.

#### on\_rollback.py

It tells DipDip how to handle chain reorgs, which is a purely application-specific logic especially if there are stateful entities. The default implementation does nothing if rollback size is 1 block and full reindexing otherwise.

#### on\_restart.py

Executed before starting indexes. Allows to configure DipDup dynamically based on data from external sources. Datasources are already initialized at the time of execution and available at `ctx.datasources`. See [Handler context](../advanced/handler-context.md) for more details how to perform configuration.

#### on\_reindex.py

#### `on_synchronized`
