# big_map

big_map index allows querying only updates of a specific big map (or several). In some cases, it can drastically reduce the amount of data transferred and speed up the indexing process.

```yaml
indexes:
  my_index:
    kind: big_map
    datasource: tzkt
    skip_history: never
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

## Index only the current state of big maps

When `skip_history` field is set to `once`, DipDup will skip historical changes only on initial sync and switch to regular indexing afterward. When the value is `always`, DipDup will fetch all big map keys on every restart. Preferrable mode depends on your workload.

All big map diffs DipDup pass to handlers during fast sync have `action` field set to `BigMapAction.ADD_KEY`. Keep in mind that DipDup fetches all keys in this mode, including ones removed from the big map. You can filter out latter by `BigMapDiff.data.active` field if needed.
