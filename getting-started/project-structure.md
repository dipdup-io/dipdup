# Project structure

## Type classes

DipDup receives all smart contract data (transaction parameters, resulting storage, big_map updates) already in normalized form ([read more](https://baking-bad.org/blog/2021/03/03/tzkt-v14-released-with-improved-smart-contract-data-and-websocket-api/) about how TzKT handles Michelson expressions), but still as raw JSON. DipDup uses contract type information to generate data classes, which allow developers to work with strictly typed data.

DipDup generates [Pydantic](https://pydantic-docs.helpmanual.io/datamodel_code_generator/) models out of JSONSchema. You might want to install additional plugins ([PyCharm](https://pydantic-docs.helpmanual.io/pycharm_plugin/), [mypy](https://pydantic-docs.helpmanual.io/mypy_plugin/)) for convenient work with this library.

The following models are created at `init`:

* `operation` indexes: storage type for all contracts met in handler patterns plus parameter type for all destination+entrypoint pairs.
* `big_map` indexes: key and storage types for all big map paths in handler configs.

### Naming convensions

Python language requires all module and function names in snake case and all class names in pascal case.

Typical imports section of big_map handler callback looks like this:

```python
from <package>.types.<typename>.storage import TypeNameStorage
from <package>.types.<typename>.parameter.<entry_point> import EntryPointParameter
from <package>.types.<typename>.big_map.<path>_key import PathKey
from <package>.types.<typename>.big_map.<path>_value import PathValue
```

Here `typename` is defined in the contract inventory, `entrypoint` is specified in the handler pattern, and `path` is in the handler config.

DipDup does not automatically handle name collisions. Use `import ... as` if multiple contracts have entrypoints that share the same name:

```python
from <package>.types.<typename>.parameter.<entry_point> import EntryPointParameter as Alias
```

## Handlers

TODO: moved to implementing handlers
### Default hooks

There is a special handlers DipDup generates for all indexes. They covers network events and initialization hooks. Names of those handlers are reserved, you can't use them in config.

#### on\_rollback.py

It tells DipDip how to handle chain reorgs, which is a purely application-specific logic especially if there are stateful entities. The default implementation does nothing if rollback size is 1 block and full reindexing otherwise.

#### on\_restart.py

Executed before starting indexes. Allows to configure DipDup dynamically based on data from external sources. Datasources are already initialized at the time of execution and available at `ctx.datasources`. See [Handler context](../advanced/handler-context.md) for more details how to perform configuration.

#### on\_reindex.py

#### `on_synchronized`

## Models

In addition to types and handlers, DipDup also generates `models` file on the top level of the package that will contain all the database models. Models file name and location are restricted by the framework and cannot be changed.

Python SDK uses Tortoise ORM for working with the database. The expected `models.py` file looks like the following:

```python
from tortoise import Model, fields


class ExampleModel(Model):
    id = fields.IntField(pk=True)
    ...
```

Check out Tortoise ORM [docs](https://tortoise-orm.readthedocs.io/en/latest/getting_started.html#tutorial) for more details.