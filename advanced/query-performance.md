# Query performance

## Postgres indexes

[Postgres indexes](https://www.postgresql.org/docs/9.5/indexes-types.html) are tables that Postgres can use to speed up data lookup. A database index acts like a pointer to data in a table - just like an index in the back of a book. If you look in the index first, you will find the data much quicker than searching the whole book (or — in this case — database).

You should add indexes on columns that often appear in `WHERE` clauses in your GraphQL queries and subscriptions.

Tortoise ORM uses BTree indexes by default. To set index on a field, just add `index=True` to the field definition:

```python
from tortoise import Model, fields


class Trade(Model):
    id = fields.BigIntField(pk=True)
    amount = fields.BigIntField()
    level = fields.BigIntField(index=True)
    timestamp = fields.DatetimeField(index=True)
```
