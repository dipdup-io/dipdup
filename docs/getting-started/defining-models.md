# Defining models

DipDup uses the Tortoise ORM library to cover database operations. During initialization, DipDup generates a `models.py` file on the top level of the package that will contain all database models. The name and location of this file cannot be changed.

A typical `models.py` file looks like the following (example from `demo_domains` package):

```python
{{ #include ../../demos/demo-domains/src/demo_domains/models.py }}
```

See the links below to learn how to use this library.

## Limitations

Some limitations are applied to model names and fields to avoid ambiguity in GraphQL API.

* Table names must be in `snake_case`
* Model fields must be in `snake_case`
* Model fields must differ from table name

> 💡 **SEE ALSO**
>
> * [Tortoise ORM documentation](https://tortoise-orm.readthedocs.io/en/latest/)
> * [Tortoise ORM examples](https://tortoise-orm.readthedocs.io/en/latest/examples.html)
> * {{ #summary deployment/database-engines.md }}
> * {{ #summary deployment/backups.md }}
