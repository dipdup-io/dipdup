# Handler context

An instance of the `HandlerContext` class is passed to every handler providing a set of helper methods and read-only properties.

## Helpers

### `.reindex()`

Drops the entire database and starts the indexing process from scratch. Currently used in the rollback handler.

### `.add_contract(name, address, typename)`

Adds new contract to the inventory.

### `.add_index(name, template, values)`

Adds new index to the current configuration.

### `.commit()`

Tells DipDup dispatcher that there are pending dynamic indexes that have to be spawned. You will need this method only if you manually change the config \(not through the `add_index` helper\).

## Properties

### `.logger`

Use this instance for logging.

### `.template_values`

You can access values used for initializing a template index.

