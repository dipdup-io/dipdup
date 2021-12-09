# dipdup run

Configures API engine\(s\) \(if specified in the configuration file\) and runs the indexer. Can be gracefully killed with `Ctrl+C` or `SIGTERM`.

```text
dipdup [-c path-to-config.yml] run [--reindex] [--oneshot]
```

DipDup will wait until database and API engines are accessible.

Use `--reindex` flag if you want to drop the database and start indexing from scratch.

Use `--oneshot` flag to just synchronize your indexes without switching to real-time updates \(useful for debugging together with `first_block` and `last_block` fields set\).

## Schema migration

DipDup does not support database schema migration: if there's any change in the models, it will reindex everything from scratch. The rationale behind is that it's easier and faster to start over rather than handle migrations that can be of arbitrary complexity and do not guarantee data consistency.

DipDup stores a hash of the SQL version of the DB schema and checks for changes each time you run this command.

## Recovering from state

DipDup applies all updates atomically block by block. In case of emergency shut down, it can safely recover later and continue from the level he ended. DipDup state is stored in the database per index and can be used by API consumer to determine current indexer head.

## Hasura setup

If [hasura](../config-reference/hasura.md) section is present in configuration file, DipDup will do basic setup:

* Ensure all tables are tracked by Hasura engine
* Enable public access to the GraphQL endpoint

## SQL scripts

DipDup will execute all the scripts from the `%project_root%/sql/**/*.sql` after the database initialization and before any indexing started.

* Scripts from `sql/on_restart` directory are executed each time you run DipDup. Those scripts may contain `CREATE OR REPLACE VIEW` or similar non-destructive operations;
* Scripts from `sql/on_reindex` directory are executed _after_ database schema is created based on `models.py` module, but _before_ indexing starts. It may be useful to change database schema in the ways that are not supported by the Tortoise ORM, e.g. to create a composite primary key;
* Both type of scripts are executed without being wrapped with transaction. It's generally a good idea to avoid touching table data in scripts;
* Scripts are executed in alphabetical order. If you're getting SQL engine errors, try to split large scripts to smaller ones;
* SQL scripts are ignored in case of SQLite database backend.

## Custom initialization

DipDup generates a default configuration hook `on_restart` that can be filled with custom initialization logic:

{% tabs %}
{% tab title="Python" %}
```python
from dipdup.context import HandlerContext


async def on_restart(ctx: HandlerContext) -> None:
    ...
```
{% endtab %}
{% endtabs %}

It can be used for creating [dynamic indexes](../config-reference/templates.md#dynamic-instances) from predefined templates or other tasks. 

{% page-ref page="../config-reference/hasura.md" %}





