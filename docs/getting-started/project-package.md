# Project package

All project ABIs, code, queries, and customizations are stored in a single Python package. The package name is defined in the `package` field of the config file.

```yaml
package: indexer
```

To generate all necessary directories and files according to config run the `init` command. You should run it every time you significantly change the config file.

The structure of package is the following (shortened for readability):

```text
indexer
├── abi                       # Contract ABIs
│   └── tzbtc
│       └── abi.json
├── graphql                   # Custom GraphQL queries for Hasura
│   └── query.graphql
├── handlers                  # User-defined callbacks to process contract data
│   ├── on_mint.py
│   └── on_transfer.py
├── hasura                    # Arbitrary Hasura metadata
│   ├── metadata.json
├── hooks                     # User-defined callbacks to run manually or on specific events
│   ├── hook.py
│   ├── on_reindex.py
│   ├── on_restart.py
│   ├── on_index_rollback.py
│   └── on_synchronized.py
├── models.py                 # DipDup ORM models
├── sql                       # SQL scripts to run manually or on specific events
│   ├── on_reindex
│   │   └── script.sql
│   ├── on_restart
│   ├── on_index_rollback
│   └── on_synchronized
└── types                     # Codegened Pydantic dataclasses for contract types
    └── tzbtc
        ├── parameter
        │   ├── mint.py
        │   └── transfer.py
        └── storage.py
```

## ABIs and typeclasses

DipDup uses contract type information to generate dataclasses for developers to work with strictly typed data. Theses dataclasses are generated automatically from contract ABIs. In most cases, you don't need to modify them manually. The process is roughly the following:

1. Contract ABIs are placed in the `abi` directory; either manually or during init.
2. DipDup converts these ABIs to intermediate JSONSchemas.
3. JSONSchemas converted to Pydantic dataclasses.

This approach allows to work with complex contract types with nested structures and polymorphic variants.

<!--
DipDup receives all smart contract data (transaction parameters, resulting storage, big_map updates) in normalized form ([read more](https://baking-bad.org/blog/2021/03/03/tzkt-v14-released-with-improved-smart-contract-data-and-websocket-api/) about how TzKT handles Michelson expressions) but still as raw JSON. DipDup uses contract type information to generate data classes, which allow developers to work with strictly typed data.

DipDup generates [Pydantic](https://pydantic-docs.helpmanual.io/datamodel_code_generator/) models out of JSONSchema. You might want to install additional plugins ([PyCharm](https://pydantic-docs.helpmanual.io/pycharm_plugin/), [mypy](https://pydantic-docs.helpmanual.io/mypy_plugin/)) for convenient work with this library.

The following models are created at `init` for different indexes:

* `operation`: storage type for all contracts in handler patterns plus parameter type for all destination+entrypoint pairs.
* `big_map`: key and storage types for all used contracts and big map paths.
* `event`: payload types for all used contracts and tags.

Other index kinds do not use code generated types.
-->

## Nested packages

Callbacks can be joined into packages to organize the project structure. Add one or multiple dots to the callback name to define nested packages:

```yaml
package: indexer
hooks:
  foo.bar:
    callback: foo.bar
```

After running the `init` command, you'll get the following directory tree:

```text
indexer
├── hooks
│   ├── foo
│   │   └── bar.py
└── sql
    └── foo
        └── bar
```

The same applies to handler callbacks. Callback alias still needs to be a valid Python module path: lowercase letters, underscores, and dots.
