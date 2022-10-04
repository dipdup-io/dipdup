# indexes

_Index_ — is a basic DipDup entity connecting the inventory and specifying data handling rules.

Each index has a unique string identifier acting as a key under the `indexes` config section:

```yaml
indexes:
  my_index:
    kind: operation
    datasource: tzkt_mainnet
```

There can be various index kinds; currently, the following options are supported for the `kind` field:

* `big_map`
* `head`
* `operation`
* `token_transfer`

There's also a special `template` kind, which is used to generate new indexes from a template during startup.

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

For a static template instance (specified in the DipDup config) there are two fields:

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
