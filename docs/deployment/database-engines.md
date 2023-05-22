# Database engines

DipDup officially supports the following databases: SQLite, PostgreSQL, TimescaleDB. This table will help you choose a database engine that mostly suits your needs.

|                    |       SQLite      |   PostgreSQL  |       TimescaleDB       |
| ------------------:|:-----------------:|:-------------:|:-----------------------:|
|    Tested versions |       latest      |   13, 14, 15  |        13, 14, 15       |
|   Best application | early development | general usage | working with timeseries |
|        SQL scripts |         ✅         |       ✅       |            ✅            |
|      Immune tables |         ❌         |       ✅       |            ✅            |
| Hasura integration |         ❌         |       ✅       |            ✅            |

By default DipDup uses in-memory SQLite database that destroys after the process exits.

While sometimes it's convenient to use one database engine for development and another one for production, be careful with specific column types that behave differently in various engines. However, Tortoise ORM mostly hides these differences.

```admonish info title="See Also"
* {{ #summary advanced/sql.md}}
* {{ #summary config/database.md}}
```
