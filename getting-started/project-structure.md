# Project structure

## Type classes

DipDup receives all smart contract data (transaction parameters, resulting storage, big_map updates) already in normalised form \([read more](https://baking-bad.org/blog/2021/03/03/tzkt-v14-released-with-improved-smart-contract-data-and-websocket-api/) about how TzKT handles Michelson expressions\), but still as raw JSON. In order for the developer to work with typed data, DipDup uses contract type information to automatically generate data classes.

In Python DipDup generates [Pydantic](https://pydantic-docs.helpmanual.io/datamodel_code_generator/) models out of JSONSchema.  
You might need to install additional [plugins](https://pydantic-docs.helpmanual.io/pycharm_plugin/) for your IDE for convenient work with Pydantic

DipDup generates only necessary models:

* For `operation` index it will generate storage type classes for all contracts met in handler patterns plus parameter type classes for all destination+entrypoint pairs.
* For `big_map` index it will generate key and storage type classes for all big map paths in handler configs.

### Naming convensions

In Python all file names are forcibly converted to snake case and all class names — to capitalized camel case.

```python
from <package>.types.<typename>.storage import TypeNameStorage
from <package>.types.<typename>.parameter.<entry_point> import (
    EntryPointParameter
)
from <package>.types.<typename>.big_map.<path>_key import PathKey
from <package>.types.name_registry.big_map.<path>_value import PathValue
```

where `typename` is defined in the contract inventory, `entrypoint` is specified in the handler pattern, and `path` is in the according Big map handler.

**NOTE** the "Storage" and "Parameter" affixes.

DipDup does not automatically handle name collisions, please use type aliases in case multiple contracts have entrypoints that share the same name.


```python
from <package>.types.<typename>.parameter.<entry_point> import (
    EntryPointParameter as Alias
)
```

## Handlers

DipDup generates a separate file with handler method stub for each callback in every index specified in configuration file.

Callback method signature is the following \(_transaction_ case\):

```python
from <package>.types.<typename>.parameter.<entry_point_1> import (
    EntryPoint1Parameter
)
from <package>.types.<typename>.parameter.<entry_point_n> import (
    EntryPointNParameter
)
from <package>.types.<typename>.storage import TypeNameStorage


async def callback(
    ctx: HandlerContext,
    entry_point_1: Transaction[EntryPoint1Parameter, TypeNameStorage],
    entry_point_n: Transaction[EntryPointNParameter, TypeNameStorage]
) -> None:
    ...
```

where:

* `entry_point_1 ... entry_point_n` are items from the according handler pattern.
* `ctx: HandlerContext` provides useful helpers and contains internal state.
* `Transaction` contains transaction amount, parameter, and storage **\(typed\)**.

For the _origination_ case the handler signature will look similar:

```python
from <package>.types.<typename>.storage import TypeNameStorage


async def on_origination(
    ctx: HandlerContext,
    origination: Origination[TypeNameStorage],
)
```

where `Origination` contains origination script, initial storage **\(typed\)**, amount, delegate, etc.

_Big map_ update handler will look like the following:

```python
from <package>.types.<typename>.big_map.<path>_key import PathKey
from <package>.types.name_registry.big_map.<path>_value import PathValue


async def on_update(
    ctx: HandlerContext,
    update: BigMapDiff[PathKey, PathValue],
)
```

where `BigMapDiff` contains action \(allocate, update, or remove\) and nullable key and value **\(typed\).**

**NOTE** that you can safely change argument names \(e.g. in case of collisions\).

{% hint style="info" %}
If you use index templates your callback methods will be reused for potentially different contract addresses. DipDup checks that all those contracts have the same **`typename`** and raises an error otherwise.
{% endhint %}

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