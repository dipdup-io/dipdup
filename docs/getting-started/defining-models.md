# Defining models

DipDup uses Tortoise ORM library to cover database operations. During initialization DipDup generates `models.py` file on the top level of the package that will contain all the database models. The name and location of this file cannot be changed.

Typical `models.py` file looks like the following:

```python
from tortoise import Tortoise, fields
from tortoise.models import Model


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    datetime = fields.DatetimeField(null=True)
```

See the links below to learn how to use this library.

## Limitations

There are some limitations introduced to make Hasura GraphQL integration easier.

* Table names must be in snake_case
* Model fields must be in snake_case
* Model fields must differ from table name

> 🤓 **SEE ALSO**
>
> * [Tortoise ORM documentation](https://tortoise-orm.readthedocs.io/en/latest/)
> * [Tortoise ORM examples](https://tortoise-orm.readthedocs.io/en/latest/examples.html)
> * [8.1. Database engines](../deployment/database-engines.md)
> * [8.9. Backup and restore](../deployment/backups.md)
