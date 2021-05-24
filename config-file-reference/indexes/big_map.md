# big\_map

Big map index allows to query only updates of a specific Big map \(or several\) — in some cases it can drastically reduce the amount of data transferred and consequently speeds up the indexing process.

```yaml
indexes:
  my_index:
    kind: big_map
    datasource: tzkt
    handlers:
      - callback: on_leger_update
        contract: contract1
        path: data.ledger
      - callback: on_token_metadata_update
        contract: contract1
        path: token_metadata
```

## Handlers

Each big\_map handler contains three required fields:

* `callback` —  name of the _async_ function with a particular [**signature**](../../command-line/dipdup-init.md#handlers); DipDup will try to load it from the module with the same name `<package_name>.handlers.<callback>`
* `contract` — Big map parent contract \(from the [inventory](../contracts.md)\)
* `path` — path to the Big map in the contract storage \(use dot as a delimiter\)

