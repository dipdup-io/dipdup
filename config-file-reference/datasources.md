---
description: Inventory block
---

# datasources

This is a list of API endpoints used to retrieve data and pass it to your indexer handlers. The obligatory field `kind` specifies which data adapter is to be used:

* `tzkt`
* `tezos-node`

### TzKT 😸

[TzKT](https://api.tzkt.io/) provides REST endpoints to query historical data and SignalR \(Websocket\) subscriptions to get real-time updates. Flexible filters allow to request only what is needed for your application and drastically speed up the indexing process.

```yaml
datasources:
  tzkt_staging_mainnet:
    kind: tzkt
    url: https://staging.api.tzkt.io
```

**NOTE** that datasource entry is basically an alias for the endpoint URI, there's no mention of the network, thus it's a good practice to add network name to the datasource alias. The reason for this design choice is to provide a generic index parameterization via the single mechanism — [templates](templates.md).

### Tezos node

Tezos RPC is a standard interface provided by the Tezos node. It's not suitable for indexing purposes, but is used for accessing mempool data and other things that are not available through TzKT.

```yaml
datasources:
  tezos_node_mainnet:
    kind: tezos-node
    url: https://mainnet-tezos.giganode.io
```

## Compatibility with indexes and plugins

|  | TzKT | Tezos node |
| :--- | :--- | :--- |
| Operation index | ✅ | ❌ |
| Big Map index | ✅ | ❌ |
| Mempool plugin \* | ✅ | ✅ |
| Metadata plugin | ✅ | ❌ |

\* — Mempool plugin requires both TzKT and Tezos node endpoints to operate.

