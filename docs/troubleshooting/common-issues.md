# Common issues

## DipDupError

### Unknown DipDup error

An unexpected error has occurred!

Please file a bug report at <https://github.com/dipdup-net/dipdup/issues>

## DatasourceError

### One of datasources returned an error

`[datasource_name]` datasource returned an error: [error_message]

Please file a bug report at <https://github.com/dipdup-net/dipdup/issues>

## ConfigurationError

### DipDup YAML config is invalid

[error_message]

DipDup config reference: <https://dipdup.net/docs/config>

## DatabaseConfigurationError

### DipDup can't initialize database with given models and parameters

[error_message]

Model: `Model`
Table: ``

Tortoise ORM examples: <https://tortoise-orm.readthedocs.io/en/latest/examples.html>
DipDup config reference: <https://dipdup.net/docs/config/database>

## ReindexingRequiredError

### Unable to continue indexing with existing database

Reindexing required! Reason: manual.

  [context_key]: [context_value]

You may want to backup database before proceeding. After that perform one of the following actions:

* Eliminate the cause of reindexing and run `dipdup schema approve`.
* Drop database and start indexing from scratch with `dipdup schema wipe` command.

See <https://dipdup.net/docs/advanced/reindexing> for more information.

## InitializationRequiredError

### Project initialization required

Project initialization required! Reason: [error_message].

Perform the following actions:

* Run `dipdup init`.
* Review and commit changes.

## ProjectImportError

### Can't import type or callback from the project package

Failed to import `[name]` from module `[module_qualname]`.

Reasons in order of possibility:

  1. `init` command has not been called after modifying the config
  2. Type or callback has been renamed or removed manually
  3. `package` name is occupied by existing non-DipDup package
  4. Package exists, but not discoverable - check `$PYTHONPATH`

## ContractAlreadyExistsError

### Attempt to add a contract with alias or address already in use

Contract with name `[name]` or address `tz1deadbeafdeadbeafdeadbeafdeadbeafdeadbeaf` already exists.

Active contracts:

## IndexAlreadyExistsError

### Attemp to add an index with an alias already in use

Index with name `[index_name]` already exists.

Active indexes:

## InvalidDataError

### Failed to validate datasource message against generated type class

Failed to validate datasource message against generated type class.

Expected type:
`type`

Invalid data:
[path]

Parsed object:
{'[key]': '[value]'}

## CallbackError

### An error occured during callback execution

`[callback_qualname]` callback execution failed:

  Exception:

Eliminate the reason of failure and restart DipDup.

## CallbackTypeError

### Agrument of invalid type was passed to a callback

`[name]` [kind] callback was called with an argument of invalid type.

  argument: `[arg]`
  type: <class 'type'>
  expected type: <class 'type'>

Make sure to set correct typenames in config and run `dipdup init --overwrite-types` to regenerate typeclasses.

## HasuraError

### Failed to configure Hasura instance

Failed to configure Hasura:

  [error_message]

Check out Hasura logs for more information.

GraphQL integration docs: <https://dipdup.net/docs/graphql/>
