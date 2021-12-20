---
description: Deployment block
---

# database

DipDup supports several database engines for development and production. The obligatory field `kind` specifies which engine has to be used:

* `sqlite`
* `postgres`

[Database engines](../deployment/database-engines.md) article may help you choose a database that better suits your needs.

### SQLite

`path` field must be either path to the .sqlite3 file or `:memory:` to keep database in memory only (default):

```yaml
database:
  kind: sqlite
  path: db.sqlite3
```

### PostgreSQL

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

## Immune tables

DipDup can drop all the tables in several cases:

* Database schema was changed
* There was a reorg that DipDup could not handle
* DipDup was started with `--reindex` flag

But sometimes you might want to keep some data because it's not sensitive to reorgs yet very resource consuming in terms of indexing. Typical example is indexing IPFS data — rollbacks do not affect off-chain storage so you can safely continue.

```yaml
database:
  immune_tables:
    - token_metadata
    - contract_metadata
```

`immune_tables` is an optional array of table names. Those tables will survive reorgs, reindexing, and even schema changes.

{% hint style="danger" %}
Note that in order to change the schema of an immune table you need to manually do a migration. DipDup will not drop the table nor automatically handle the update.
{% endhint %}
