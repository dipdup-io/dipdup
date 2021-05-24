---
description: Indexes block
---

# indexes

_Index_ — is a basic DipDup entity connecting together the inventory and specifying data handling rules.

Each index has a unique string identifier acting as a key under `indexes` config section:

```yaml
indexes:
  my_index:
    kind: operation
    datasource: tzkt_mainnet
```

There can be various index kinds, currently three possible options are supported for the `kind` field:

* `operation`
* `big_map`
* `template`

All the indexes have to specify `datasource` field which is an alias of an existing entry under the [datasources](../datasources.md) section.

## Indexing scope

One can optionally specify block levels DipDup has to start and stop indexing at, e.g. there's a new version of the contract and it will be more efficient to stop handling the old one.

```yaml
indexes:
  my_index:
    first_block: 1000000
    last_block: 2000000
```

