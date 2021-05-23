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

