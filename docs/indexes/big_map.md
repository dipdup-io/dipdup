# `big_map` index

`big_map` index allows querying only updates of specific big maps. In some cases, it can drastically reduce the amount of data transferred and thus indexing speed compared to fetching all operations.

```yaml
indexes:
  token_big_map_index:
    kind: big_map
    datasource: tzkt
    skip_history: never
    handlers:
      - callback: on_ledger_update
        contract: token
        path: data.ledger
      - callback: on_token_metadata_update
        contract: token
        path: token_metadata
```

## Handlers

Each big map handler contains three required fields:

* `callback` —  a name of async function with a particular signature; DipDup will search for it in `<package>.handlers.<callback>` module.
* `contract` — big map parent contract
* `path` — path to the big map in the contract storage (use dot as a delimiter)

## Index only the current state

When the `skip_history` field is set to `once`, DipDup will skip historical changes only on initial sync and switch to regular indexing afterward. When the value is `always`, DipDup will fetch all big map keys on every restart. Preferrable mode depends on your workload.

All big map diffs DipDup passes to handlers during fast sync have the `action` field set to `BigMapAction.ADD_KEY`. Remember that DipDup fetches all keys in this mode, including ones removed from the big map. You can filter them out later by `BigMapDiff.data.active` field if needed.
