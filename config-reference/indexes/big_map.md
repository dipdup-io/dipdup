# big_map

big_map index allows querying only updates of a specific big map (or several). In some cases, it can drastically reduce the amount of data transferred and speed up the indexing process.

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

* `callback` —  name of the _async_ function with a particular [**signature**](../../cli-reference/init.md#handlers); DipDup will try to load it from the module with the same name `<package_name>.handlers.<callback>`
* `contract` — Big map parent contract (from the [inventory](../contracts.md))
* `path` — path to the Big map in the contract storage (use dot as a delimiter)
