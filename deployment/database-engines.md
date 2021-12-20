# Database engines

DipDup officially supports the following databases: SQLite, PostgreSQL, TimescaleDB. This page will help you choose a database engine that mostly suits your needs.

| | SQLite | PostgreSQL | TimescaleDB |
|-| | | |
| Supported versions | any | any | any |
| When to use | early development | general usage | working with timeseries
| Performance | good | better | great in some scenarios |
| SQL hooks | ❌ | ✅ | ✅ |
| Immune tables\* | ❌ | ✅ | ✅ |
| Hasura integration | ❌ | ✅\*\*| ✅\*\*|

\* — see reindexing

\*\* — schema name must be `public`
