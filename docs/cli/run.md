# run

Configures API connectors, initializes database and runs the indexer. Execution can be gracefully interrupted with `Ctrl+C` or `SIGTERM` signal.

```shell
dipdup [-c dipdup.yml] run [--postpone-jobs] [--early-realtime] [--merge-subscriptions]
```

## Hasura setup

If [hasura](../config/hasura.md) section is present in configuration file, DipDup will do basic setup:

* Ensure all tables are tracked by Hasura engine
* Enable public access to the GraphQL endpoint

## SQL scripts

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

DipDup will execute all the scripts from the `<package>/sql/**/*.sql` after the database initialization and before any indexing starts.

* Scripts from `sql/on_restart` directory are executed each time you run DipDup. Those scripts may contain `CREATE OR REPLACE VIEW` or similar non-destructive operations;
* Scripts from `sql/on_reindex` directory are executed _after_ database schema is created based on `models.py` module, but _before_ indexing starts. It may be useful to change database schema in the ways that are not supported by the Tortoise ORM, e.g. to create a composite primary key;
* Both types of scripts are executed without being wrapped with SQL transactions. It's generally a good idea to avoid touching table data in scripts;
* SQL scripts are ignored if SQLite is used as a database backend.

## Custom initialization

DipDup generates a default configuration hook `on_restart` that can be filled with custom initialization logic:

```python
from dipdup.context import HandlerContext


async def on_restart(ctx: HandlerContext) -> None:
    ...
```

It can be used for creating [dynamic indexes](../config/templates.md#dynamic-instances) from predefined templates or other tasks.
