# Project structure

The structure of the DipDup project package is the following:

```text
demo_token
├── graphql
├── handlers
│   ├── __init__.py
│   ├── on_mint.py
│   └── on_transfer.py
├── hasura
├── hooks
│   ├── __init__.py
│   ├── on_reindex.py
│   ├── on_restart.py
│   ├── on_index_rollback.py
│   └── on_synchronized.py
├── __init__.py
├── models.py
├── sql
│   ├── on_reindex
│   ├── on_restart
│   ├── on_index_rollback
│   └── on_synchronized
└── types
    ├── __init__.py
    └── tzbtc
        ├── __init__.py
        ├── parameter
        │   ├── __init__.py
        │   ├── mint.py
        │   └── transfer.py
        └── storage.py
```

| path        | description                                                            |
| ----------- | ---------------------------------------------------------------------- |
| `graphql`   | GraphQL queries for Hasura (`*.graphql`)                               |
| `handlers`  | User-defined callbacks to process matched operations and big map diffs |
| `hasura`    | Arbitrary Hasura metadata (`*.json`)                                   |
| `hooks`     | User-defined callbacks to run manually or by schedule                  |
| `models.py` | Tortoise ORM models                                                    |
| `sql`       | SQL scripts to run from callbacks (`*.sql`)                            |
| `types`     | Codegened Pydantic typeclasses for contract storage/parameter          |

DipDup will generate all the necessary directories and files inside the project's root on `init` command. These include contract type definitions and callback stubs to be implemented by the developer.

## Type classes

<!-- TODO: Move somewhere -->

DipDup receives all smart contract data (transaction parameters, resulting storage, big_map updates) in normalized form ([read more](https://baking-bad.org/blog/2021/03/03/tzkt-v14-released-with-improved-smart-contract-data-and-websocket-api/) about how TzKT handles Michelson expressions) but still as raw JSON. DipDup uses contract type information to generate data classes, which allow developers to work with strictly typed data.

DipDup generates [Pydantic](https://pydantic-docs.helpmanual.io/datamodel_code_generator/) models out of JSONSchema. You might want to install additional plugins ([PyCharm](https://pydantic-docs.helpmanual.io/pycharm_plugin/), [mypy](https://pydantic-docs.helpmanual.io/mypy_plugin/)) for convenient work with this library.

The following models are created at `init` for different indexes:

* `operation`: storage type for all contracts in handler patterns plus parameter type for all destination+entrypoint pairs.
* `big_map`: key and storage types for all used contracts and big map paths.
* `event`: payload types for all used contracts and tags.

Other index kinds do not use code generated types.

## Nested packages

Callback modules don't have to be in top-level `hooks`/`handlers` directories. Add one or multiple dots to the callback name to define nested packages:

```yaml
package: indexer
hooks:
  foo.bar:
    callback: foo.bar
```

After running the `init` command, you'll get the following directory tree (shortened for readability):

```text
indexer
├── hooks
│   ├── foo
│   │   ├── bar.py
│   │   └── __init__.py
│   └── __init__.py
└── sql
    └── foo
        └── bar
            └── .keep
```

The same rules apply to handler callbacks. Note that the `callback` field must be a valid Python package name - lowercase letters, underscores, and dots.

```admonish info title="See Also"
* {{ #summary getting-started/defining-models.md }}
* {{ #summary getting-started/implementing-handlers.md }}
* {{ #summary advanced/hooks.md }}
* {{ #summary advanced/sql.md }}
* {{ #summary graphql/hasura.md }}
```
