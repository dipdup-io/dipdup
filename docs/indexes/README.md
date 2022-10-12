# Indexes

_Index_ — is a primary DipDup entity connecting the inventory and specifying data handling rules.

Each index has a linked TzKT datasource and a set of handlers. Indexes can join multiple contracts considered as a single application. Also, contracts can be used by multiple indexes of any kind, but make sure that data don't overlap. See {{ #summary getting-started/core-concepts.md#atomicity-and-persistency }}.

```yaml
indexes:
  contract_operations:
    kind: operation
    datasource: tzkt_mainnet
    handlers:
      - callback: on_operation
        pattern: ...
```

Multiple indexes are available for different kinds of blockchain data. Currently, the following options are available:

* `big_map`
* `event`
* `head`
* `operation`
* `token_transfer`

Every index is linked to specific datasource from {{ #summary config/datasources.md }} config section.

## Using templates

Index definitions can be templated to reduce the amount of boilerplate code. To create an index from the template during startup, add an item with the `template` and `values` field to the `indexes` section:

```yaml
templates:
  operation_index_template:
    kind: operation
    datasource: <datasource>
    ...

indexes:
  template_instance:
    template: operation_index_template
    values:
      datasource: tzkt_mainnet
```

You can also create indexes from templates later in runtime. See {{ #summary getting-started/templates-and-variables.md }} page.

## Indexing scope

One can optionally specify block levels DipDup has to start and stop indexing at, e.g., there's a new version of the contract, and there's no need to track the old one anymore.

```yaml
indexes:
  my_index:
    first_level: 1000000
    last_level: 2000000
```
