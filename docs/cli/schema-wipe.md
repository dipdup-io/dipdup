# schema wipe

Drop all database tables, functions, and views.

> ⚠ **WARNING**
>
> This action is irreversible! All indexed data will be lost!

```shell
dipdup schema wipe [--immune]
```

Add `--immune` flag to drop immune tables too. See [12.3. database](../config/database.md#postgresql) to learn about immune tables.
