# dipdup run

Configures API engine\(s\) \(if specified in the configuration file\) and runs the indexer. Can be gracefully killed with `Ctrl+C` or `SIGTERM`.

```text
dipdup [-c path-to-config.yml] run
```

DipDup will wait until database and API engines are accessible.

## Schema migration

DipDup does not support database schema migration: if there's any change in the models, it will reindex everything from scratch. The rationale behind is that it's easier and faster to start over rather than handle migrations that can be of arbitrary complexity and do not guarantee data consistency.

DipDup stores a hash of the SQL version of the DB schema and checks for changes each time you run this command.

## Recovering from state

DipDup applies all updates atomically block by block. In case of emergency shut down, it can safely recover later and continue from the level he ended. DipDup state is stored in the database per index and can be used by API consumer to determine current indexer head.

## Hasura setup

If [hasura](../config-file-reference/hasura.md) section is present in configuration file, DipDup will do basic setup:

* Ensure all tables are tracked by Hasura engine
* Enable public access to the GraphQL endpoint

## SQL scripts

DipDup will execute all the scripts from the `%project_root%/sql` after the database initialization and before any indexing istarted.



{% page-ref page="../config-file-reference/hasura.md" %}





