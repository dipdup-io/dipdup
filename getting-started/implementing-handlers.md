# Implementing handlers

DipDup generates a separate file with a callback stub for each handler in every index specified in the configuration file.

In case of `transaction` handler, callback method signature is the following:

```python
from <package>.types.<typename>.parameter.<entry_point_1> import EntryPoint1Parameter
from <package>.types.<typename>.parameter.<entry_point_n> import EntryPointNParameter
from <package>.types.<typename>.storage import TypeNameStorage


async def on_transaction(
    ctx: HandlerContext,
    entry_point_1: Transaction[EntryPoint1Parameter, TypeNameStorage],
    entry_point_n: Transaction[EntryPointNParameter, TypeNameStorage]
) -> None:
    ...
```

where:

* `entry_point_1 ... entry_point_n` are items from the according handler pattern.
* `ctx: HandlerContext` provides useful helpers and contains an internal state (see ).
* `Transaction` contains transaction typed parameter and storage, plus other fieds.

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
