# Query performance

## Postgres indexes

[Postgres indexes](https://www.postgresql.org/docs/9.5/indexes-types.html) are special lookup tables that Postgres can use to speed up data lookup. An index acts as a pointer to data in a table, and it works very similar to an index in the back of a book. If you look in the index first, you’ll find the data much quicker than searching the whole book \(or — in this case — database\).

Set indexes on columns that appear in "where" clauses in your GraphQL queries and subscriptions.

{% tabs %}
{% tab title="Python" %}
Tortoise ORM allows to use all types of PG indexes but by default it uses BTree. In order to set index on a field just add `index=True`

```python
from tortoise import Model, fields


class Trade(Model):
    id = fields.BigIntField(pk=True)
    amount = fields.BigIntField()
    level = fields.BigIntField(index=True)
    timestamp = fields.DatetimeField(index=True)
```
{% endtab %}
{% endtabs %}

