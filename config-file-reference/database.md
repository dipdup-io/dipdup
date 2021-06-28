---
description: Deployment block
---

# database

DipDup supports several database engines for development and production. The obligatory field `kind` specifies which engine has to be used:

* `sqlite`
* `postgres`
* `mysql`

### SQLite

Requires `path` to the sqlite3 file, either relative or absolute:

```yaml
database:
  kind: sqlite
  path: db.sqlite3
```

{% hint style="info" %}
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

### MySQL

Requires `host`, `port`, `user`, `password`, and `database` fields.

```yaml
database:
  kind: mysql
  host: db
  port: 5432
  user: dipdup
  password: ${MYSQL_PASSWORD:-changeme}
  database: dipdup
```

## Compatibility with API engines

While DipDup itself \(actually the ORM used internally\) abstracts developer from particular DB engine implementation, when it comes to exposing API endpoints there are some limitations depending on your API engine choice.

|  | Hasura | PostgREST |
| :--- | :--- | :--- |
| SQLite | ❌ | ❌ |
| Postgres | ✅ | ✅ |
| MySQL | ✅ | ❌ |



