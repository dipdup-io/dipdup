# Hooks

Hooks are user-defined callbacks called either from the `ctx.fire_hook` method or by the job scheduler.

Let's assume we want to calculate some statistics on-demand to avoid blocking an indexer with heavy computations. Add the following lines to the DipDup config:

```yaml
hooks:
  calculate_stats:
    callback: calculate_stats
    atomic: False
    args:
     major: bool
     depth: int
```

Here are a couple of things here to pay attention to:

* An `atomic` option defines whether the hook callback will be wrapped in a single SQL transaction or not. If this option is set to true main indexing loop will be blocked until hook execution is complete. Some statements, like `REFRESH MATERIALIZED VIEW`, do not require to be wrapped in transactions, so choosing a value of the `atomic` option could decrease the time needed to perform initial indexing.
* Values of `args` mapping are used as type hints in a signature of a generated callback. We will return to this topic later in this article.

Now it's time to call `dipdup init`. The following files will be created in the project's root:

```text
├── hooks
│   └── calculate_stats.py
└── sql
    └── calculate_stats
        └── .keep
```

Content of the generated callback stub:

```python
from dipdup.context import HookContext

async def calculate_stats(
    ctx: HookContext,
    major: bool,
    depth: int,
) -> None:
    await ctx.execute_sql('calculate_stats')
```

By default, hooks execute SQL scripts from the corresponding subdirectory of `sql/`. Remove or comment out the `execute_sql` call to prevent this. This way, both Python and SQL code may be executed in a single hook if needed.

## Arguments typechecking

DipDup will ensure that arguments passed to the hooks have the correct types when possible. `CallbackTypeError` exception will be raised otherwise. Values of an `args` mapping in a hook config should be either built-in types or `__qualname__` of external type like `decimal.Decimal`. Generic types are not supported: hints like `Optional[int] = None` will be correctly parsed during codegen but ignored on type checking.

> 💡 **SEE ALSO**
>
> * {{ #summary config/hooks.md}}
