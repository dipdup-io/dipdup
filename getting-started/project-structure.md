# Project structure

The structure of DipDup project package is the following:

```text
demo_tzbtc
├── graphql
├── handlers
│   ├── __init__.py
│   ├── on_mint.py
│   └── on_transfer.py
├── hooks
│   ├── __init__.py
│   ├── on_reindex.py
│   ├── on_restart.py
│   ├── on_rollback.py
│   └── on_synchronized.py
├── __init__.py
├── models.py
├── sql
│   ├── on_reindex
│   ├── on_restart
│   ├── on_rollback
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

| path | description |
| - | - |
| `graphql` | GraphQL queries for Hasura (`*.graphql`) |
| `handlers` | User-defined callbacks to process matched operations and big map diffs |
| `hooks` | User-defined callbacks to run manually or by schedule |
| `models.py` | Tortoise ORM models |
| `sql` | SQL scripts to run from callbacks (`*.sql`) | 
| `types` | Codegened Pydantic typeclasses for contract storage/parameter |

> 🤓 **SEE ALSO**
>
> * [4.6. Defining models](defining-models.md)
> * [4.7. Implementing handlers](implementing-handlers.md)
> * [5.2. Hooks](../advanced/hooks/README.md)
> * [5.5. Executing SQL scripts](../advanced/sql.md)
> * [5.6.1. Hasura integration](../graphql/hasura.md)

## `types`: type classes

<!-- TODO: Move somewhere -->

DipDup receives all smart contract data (transaction parameters, resulting storage, big_map updates) already in normalized form ([read more](https://baking-bad.org/blog/2021/03/03/tzkt-v14-released-with-improved-smart-contract-data-and-websocket-api/) about how TzKT handles Michelson expressions), but still as raw JSON. DipDup uses contract type information to generate data classes, which allow developers to work with strictly typed data.

DipDup generates [Pydantic](https://pydantic-docs.helpmanual.io/datamodel_code_generator/) models out of JSONSchema. You might want to install additional plugins ([PyCharm](https://pydantic-docs.helpmanual.io/pycharm_plugin/), [mypy](https://pydantic-docs.helpmanual.io/mypy_plugin/)) for convenient work with this library.

The following models are created at `init`:

* `operation` indexes: storage type for all contracts met in handler patterns plus parameter type for all destination+entrypoint pairs.
* `big_map` indexes: key and storage types for all big map paths in handler configs.
