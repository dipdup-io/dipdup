# Callback context (`ctx`)

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

An instance of the `HandlerContext` class is passed to every handler providing a set of helper methods and read-only properties.

## `.reindex() -> None`

Drops the entire database and starts the indexing process from scratch. `on_rollback` hook calls this helper by default.

## `.add_contract(name, address, typename) -> Coroutine`

Add a new contract to the inventory.

## `.add_index(name, template, values) -> Coroutine`

Add a new index to the current configuration.

## `.fire_hook(name, wait=True, **kwargs) -> None`

Trigger hook execution. Unset `wait` to execute hook outside of the current database transaction.

## `.execute_sql(name) -> None`

The `execute_sql` argument could be either name of SQL script in `sql` directory or an absolute/relative path. If the path is a directory, all `.sql` scripts within it will be executed in alphabetical order.

## `.update_contract_metadata(network, address, token_id, metadata) -> None`

Inserts or updates the corresponding row in the service `dipdup_contract_metadata` table used for exposing the [5.11 Metadata interface](../metadata-interface.md)

## `.update_token_metadata(network, address, token_id, metadata) -> None`

Inserts or updates the corresponding row in the service `dipdup_token_metadata` table used for exposing the [5.11 Metadata interface](../metadata-interface.md)

## `.logger`

Use this instance for logging.

## `.template_values`

You can access values used for initializing a template index.
