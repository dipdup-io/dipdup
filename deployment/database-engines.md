# Database engines

DipDup officially supports the following databases: SQLite, PostgreSQL, TimescaleDB. This page will help you choose a database engine that mostly suits your needs.

| | SQLite | PostgreSQL | TimescaleDB |
|---| --- | --- | --- |
| Supported versions | any | any | any |
| When to use | early development | general usage | working with timeseries
| Performance | good | better | great in some scenarios |
| SQL hooks | ❌ | ✅ | ✅ |
| Immune tables\* | ❌ | ✅ | ✅ |
| Hasura integration | ❌ | ✅\*\*| ✅\*\*|

\* — see [`immune_tables` config reference](../config-reference/database.md#immune-tables) for details.

\*\* — schema name must be `public`

While sometimes it's convenient to use one database engine for development and another one for production, be careful with specific column types that behave differently in various engines.
