# Implementing handlers

DipDup generates a separate file with a callback stub for each handler in every index specified in the configuration file.

In the case of the `transaction` handler, the callback method signature is the following:

<!-- FIXME: Includes -->

```python
from <package>.types.<typename>.parameter.entrypoint_foo import EntryPointFooParameter
from <package>.types.<typename>.parameter.entrypoint_bar import EntryPointBarParameter
from <package>.types.<typename>.storage import TypeNameStorage


async def on_transaction(
    ctx: HandlerContext,
    entrypoint_foo: Transaction[EntryPointFooParameter, TypeNameStorage],
    entrypoint_bar: Transaction[EntryPointBarParameter, TypeNameStorage]
) -> None:
    ...
```

where:

* `entrypoint_foo ... entrypoint_bar` are items from the according to handler pattern.
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

## Handling name collisions

Indexing operations of multiple contracts with the same entrypoints can lead to name collisions during code generation. In this case DipDup raises a `ConfigurationError` and suggests to set alias for each conflicting handler. That applies to `operation` indexes only. Consider the following index definition, some kind of "chain minting" contract:

```yaml
kind: operation
handlers:
  - callback: on_mint
    pattern:
    - type: transaction
      entrypoint: mint
      alias: foo_mint
    - type: transaction
      entrypoint: mint
      alias: bar_mint
```

The following code will be generated for `on_mint` callback:

```python
from example.types.foo.parameter.mint import MintParameter as FooMintParameter
from example.types.foo.storage import FooStorage
from example.types.bar.parameter.mint import MintParameter as BarMintParameter
from example.types.bar.storage import BarStorage


async def on_transaction(
    ctx: HandlerContext,
    foo_mint: Transaction[FooMintParameter, FooStorage],
    bar_mint: Transaction[BarMintParameter, BarStorage]
) -> None:
    ...
```

You can safely change argument names if you want to.
