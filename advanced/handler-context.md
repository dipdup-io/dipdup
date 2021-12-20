# Handler context

## Handler context

An instance of the `HandlerContext` class is passed to every handler providing a set of helper methods and read-only properties.

### `.reindex() -> None`

Drops the entire database and starts the indexing process from scratch. Currently used in the rollback handler.

### `.add_contract(name, address, typename) -> Coroutine`

Adds new contract to the inventory.

### `.add_index(name, template, values) -> Coroutine`

Adds new index to the current configuration.

### `.fire_hook(name, **kwargs) -> None`

You can trigger hook execution either from handler callback or by job schedule. Or even from another hook if you're brave enough.

### `.execute_sql(filename) -> None`

The `execute_sql` argument could be either name of a file/directory inside of the `sql` project directory or an absolute/relative path. If the path is a directory, all scripts having the `.sql` extension within it will be executed in alphabetical order.

## Properties

### `.logger`

Use this instance for logging.

### `.template_values`

You can access values used for initializing a template index.
