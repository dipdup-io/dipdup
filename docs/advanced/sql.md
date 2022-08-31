# SQL scripts

Put your `*.sql` scripts to `<package>/sql`. You can run these scripts from any callback with `ctx.execute_sql('name')`. If `name` is a directory, each script it contains will be executed.

Scripts are executed without being wrapped with SQL transactions. It's generally a good idea to avoid touching table data in scripts.

SQL scripts are ignored if SQLite is used as a database backend.

By default, an empty `sql/<hook_name>` directory is generated for every hook in config during init. Remove `ctx.execute_sql` call from hook callback to avoid executing them.

## Event hooks

Scripts from `sql/on_restart` directory are executed each time you run DipDup. Those scripts may contain `CREATE OR REPLACE VIEW` or similar non-destructive operations.

Scripts from `sql/on_reindex` directory are executed _after_ the database schema is created based on the `models.py` module but _before_ indexing starts. It may be useful to change the database schema in ways that are not supported by the Tortoise ORM, e.g., to create a composite primary key.

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/event-hooks.md}}
