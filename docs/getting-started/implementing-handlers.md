# Implementing handlers

DipDup generates a separate file with a callback stub for each handler in every index specified in the configuration file.

In the case of the `transaction` handler, the callback method signature is the following:

```python
from <package>.types.<typename>.parameter.<entrypoint_1> import EntryPoint1Parameter
from <package>.types.<typename>.parameter.<entrypoint_n> import EntryPointNParameter
from <package>.types.<typename>.storage import TypeNameStorage


async def on_transaction(
    ctx: HandlerContext,
    entrypoint_1: Transaction[EntryPoint1Parameter, TypeNameStorage],
    entrypoint_n: Transaction[EntryPointNParameter, TypeNameStorage]
) -> None:
    ...
```

where:

* `entrypoint_1 ... entrypoint_n` are items from the according to handler pattern.
* `ctx: HandlerContext` provides useful helpers and contains an internal state (see ).
* A `Transaction` model contains transaction typed parameter and storage, plus other fields.

For the _origination_ case, the handler signature will look similar:

```python
from <package>.types.<typename>.storage import TypeNameStorage


async def on_origination(
    ctx: HandlerContext,
    origination: Origination[TypeNameStorage],
)
```

An `Origination` model contains the origination script, initial storage (typed), amount, delegate, etc.

A _Big\_map_ update handler will look like the following:

```python
from <package>.types.<typename>.big_map.<path>_key import PathKey
from <package>.types.<typename>.big_map.<path>_value import PathValue


async def on_update(
    ctx: HandlerContext,
    update: BigMapDiff[PathKey, PathValue],
)
```

`BigMapDiff` contains action (allocate, update, or remove), nullable key and value (typed).

You can safely change argument names (e.g., in case of collisions).

<!--
TODO: Rewrite

> 💡 **TIP**
>
> If you use index templates, your callback methods will be reused for potentially different contract addresses. DipDup checks that all those contracts have the same `typename` and raise an error otherwise.
-->

## Naming conventions

Python language requires all module and function names in snake case and all class names in pascal case.

A typical imports section of `big_map` handler callback looks like this:

```python
from <package>.types.<typename>.storage import TypeNameStorage
from <package>.types.<typename>.parameter.<entrypoint> import EntryPointParameter
from <package>.types.<typename>.big_map.<path>_key import PathKey
from <package>.types.<typename>.big_map.<path>_value import PathValue
```

Here `typename` is defined in the contract inventory, `entrypoint` is specified in the handler pattern, and `path` is in the handler config.

DipDup does not automatically handle name collisions. Use `import ... as` if multiple contracts have entrypoints that share the same name:

```python
from <package>.types.<typename>.parameter.<entrypoint> import EntryPointParameter as Alias
```
