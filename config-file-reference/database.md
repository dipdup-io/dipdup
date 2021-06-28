---
description: Deployment block
---

# database

DipDup supports several database engines for development and production. The obligatory field `kind` specifies which engine has to be used:

* `sqlite`
* `postgres`

### SQLite

Requires `path` to the sqlite3 file, either relative or absolute:

```yaml
database:
  kind: sqlite
  path: db.sqlite3
```

{% hint style="warning" %}
**NOTE**: while it's sometimes convenient to use one database engine for development and another one for production, be careful with specific column types that behave differently in various engines.
{% endhint %}

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

{% hint style="info" %}
You can use compose-style environment variable substitutions with default values for secrets \(and all fields in general\).
{% endhint %}

## Compatibility with API engines

While DipDup itself \(actually the ORM used internally\) abstracts developer from particular DB engine implementation, when it comes to exposing API endpoints there are some limitations depending on your API engine choice.

|  | Hasura | PostgREST |
| :--- | :--- | :--- |
| SQLite | ❌ | ❌ |
| Postgres | ✅ | ✅ |

## "Immune" tables

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

