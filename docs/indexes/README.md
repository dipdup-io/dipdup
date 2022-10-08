# indexes

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
* `head`
* `operation`
* `token_transfer`

There's also a special `template` kind to generate new indexes from a template during startup.

All the indexes have to specify the `datasource` field, an alias of an existing entry under the [datasources](../datasources.md) section.

# Templates

This index type is used for creating a static template instance.

```yaml
indexes:
  my_index:
    template: my_template
    values:
      placeholder1: value1
      placeholder2: value2
```

By static, we mean that the index is defined in the config file and not created in runtime. See {{ #summary getting-started/templates-and-variables.md }.

For a static template instance (specified in the DipDup config), there are two fields:

* `template` — template name (from [templates](../templates.md) section)
* `values` — concrete values for each [placeholder](../templates.md#placeholders) used in a chosen template

## Indexing scope

One can optionally specify block levels DipDup has to start and stop indexing at, e.g., there's a new version of the contract, and there's no need to track the old one anymore.

```yaml
indexes:
  my_index:
    first_level: 1000000
    last_level: 2000000
```
