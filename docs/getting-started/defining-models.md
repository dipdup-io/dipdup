# Defining models

DipDup uses [Tortoise ORM](https://tortoise.github.io/examples.html) library to work with database. It's fast, flexible, and similar to Django ORM.

Please, don't report DipDup issues to the Tortoise ORM bugtracker! We patch it heavily to better suit our needs.

Project models should be placed in `models.py` file and inherit from `dipdup.models.Model` class. A typical module looks like this (example from the `demo-domains`)

```python
{{ #include ../../src/demo_domains/models/__init__.py }}
```

Now you can use these models in your callbacks.

```python
tld = await TLD.filter(id='tez').first()
tld.owner = 'tz1deadbeefdeadbeefdeadbeefdeadbeef'
await tld.save()
```

Visit [Tortose ORM docs](https://tortoise.github.io/examples.html) for more examples.

## Limitations

Some limitations are applied to model names and fields to avoid ambiguity in GraphQL API.

* Table names must be in `snake_case`
* Model fields must be in `snake_case`
* Model fields must differ from table name

```admonish info title="See Also"
* {{ #summary deployment/database-engines.md }}
* {{ #summary deployment/backups.md }}
```
