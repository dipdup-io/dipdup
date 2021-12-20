# database

DipDup supports several database engines for development and production. The obligatory field `kind` specifies which engine has to be used:

* `sqlite`
* `postgres`

[Database engines](../deployment/database-engines.md) article may help you choose a database that better suits your needs.

## SQLite

`path` field must be either path to the .sqlite3 file or `:memory:` to keep database in memory only (default):

```yaml
database:
  kind: sqlite
  path: db.sqlite3
```

## PostgreSQL

Requires `host`, `port`, `user`, `password`, and `database` fields. Also it's possible to specify `schema_name` if it differs from _public_.

```yaml
database:
  kind: postgres
  host: db
  port: 5432
  user: dipdup
  password: ${POSTGRES_PASSWORD:-changeme}
  database: dipdup
  schema_name: custom
```

You can use compose-style environment variable substitutions with default values for secrets and other fields. See [Templates and variables](../getting-started/templates-and-variables.md#) for details.

### Immune tables

In some cases, DipDup can't continue indexing with an existing database. See [Reindexing](../advanced/reindexing.md) for details. One of the solutions to resolve reindexing state is to drop the database and start indexing from scratch. To achieve this, either invoke [`schema wipe` command](../cli-reference/schema-wipe.md) or set an action to `wipe` in [`advanced.reindex` config section](../config-reference/advanced.md).

You might want to keep several tables during schema wipe if data in them is not dependent on index states yet heavy. A typical example is indexing IPFS data — rollbacks do not affect off-chain storage, so you can safely continue after receiving reorg message.

```yaml
database:
  immune_tables:
    - token_metadata
    - contract_metadata
```

`immune_tables` is an optional array of table names. Those tables will survive reorgs, reindexing, and even schema changes.

Note that to change the schema of an immune table, you need to perform a migration by yourself. DipDup will neither drop the table nor automatically handle the update.
