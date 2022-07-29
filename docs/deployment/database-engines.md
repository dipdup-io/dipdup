# Database engines

DipDup officially supports the following databases: SQLite, PostgreSQL, TimescaleDB. This table will help you choose a database engine that mostly suits your needs.

| | SQLite | PostgreSQL | TimescaleDB |
| -: | :-: | :-: | :-: |
| Supported versions | `latest` | `13`, `14`, `15` | `pg13`, `pg14` |
| When to use | early development | general usage | working with timeseries
| Performance | good | better | great in some scenarios |
| SQL scripts | ❌ | ✅ | ✅ |
| Immune tables | ❌ | ✅ | ✅ |
| Hasura integration | ❌ | ✅ | ✅ |

While sometimes it's convenient to use one database engine for development and another one for production, be careful with specific column types that behave differently in various engines.

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/sql.md}}
> * {{ #summary config/database.md#immune-tables}}
