---
description: Inventory block
---

# datasources

This is a list of API endpoints used to retrieve data and pass it to your indexer handlers. The obligatory field `kind` specifies which data adapter is to be used:

* `tzkt`
* `bcd`
* `tezos-node`

## Datasources

### TzKT 😸

[TzKT](https://api.tzkt.io/) provides REST endpoints to query historical data and SignalR \(Websocket\) subscriptions to get realtime updates. Flexible filters allow to request only what is needed for your application and drastically speed up the indexing process.

```yaml
datasources:
  tzkt_mainnet:
    kind: tzkt
    url: https://api.tzkt.io
```

**NOTE** that datasource entry is basically an alias for the endpoint URI, there's no mention of the network, thus it's a good practice to add network name to the datasource alias. The reason for this design choice is to provide a generic index parameterization via the single mechanism — [templates](templates.md).

### Better Call Dev

Better Call Dev is another blockchain explorer and API with functionality similar to TzKT. It can't be used as a main datasource for indexer and mempool/metadata plugins but you can call it from inside of handlers to gather additional data.

```yaml
datasources:
  bcd_mainnet:
    kind: bcd
    url: https://api.better-call.dev
    network: mainnet

```

### Tezos node

Tezos RPC is a standard interface provided by the Tezos node. It's not suitable for indexing purposes, but is used for accessing mempool data and other things that are not available through TzKT.

```yaml
datasources:
  tezos_node_mainnet:
    kind: tezos-node
    url: https://mainnet-tezos.giganode.io
```

### Coinbase

A connector for [Coinbase Pro API \(opens new window\)](https://docs.pro.coinbase.com/). Provides `get_candles` and `get_oracle_data` methods. May be useful in enriching indexes of DeFi contracts with off-chain data.

```yaml
datasources:
  coinbase:
    kind: coinbase
```

Please note that Coinbase can't be used as an index datasource instead of TzKT. It can be accessed via `ctx.datasources` mapping in either handlers or jobs.

## Advanced HTTP settings

All datasources now share the same code under the hood to communicate with underlying APIs via HTTP. Configs of all datasources and also Hasura's one can contain an optional section `http` with any number of the following parameters set:

```yaml
datasources:
  tzkt:
    kind: tzkt
    ...
    http:
      cache: True
      retry_count: 10
      retry_sleep: 1
      retry_multiplier: 1.2
      ratelimit_rate: 100
      ratelimit_period: 60
      connection_limit: 25
      batch_size: 10000
hasura:
  url: http://hasura:8080
  http:
    ...
```

Each datasource has its own defaults. Usually there's no reason to alter these settings unless you use your own instance of TzKT or BCD.

By default, DipDup retries failed requests infinitely with exponentially increasing delay between attempts. Set `retry_count` parameter in order to limit the number of attempts.

`batch_size` parameter is TzKT-specific. By default, DipDup limit requests to 10000 items, the maximum value allowed on public instances provided by Baking Bad. Decreasing this value will lead to reducing time required for TzKT to process a single request and thus reduce the load. Same effect but limited to synchronizing multiple indexes concurrently can be achieved with reducing `connection_limit` parameter.

## Compatibility with indexes and plugins

|  | TzKT | Tezos node | BCD | Coinbase |
| :--- | :--- | :--- | :--- | :--- |
| Operation index | ✅ | ❌ | ❌ | ❌ |
| Big Map index | ✅ | ❌ | ❌ | ❌ |
| Handlers \* | ✅ | ✅ | ✅ | ✅ |
| Mempool plugin \*\* | ✅ | ✅ | ❌ | ❌ |
| Metadata plugin | ✅ | ❌ | ❌ | ❌ |

\* Available at `ctx.datasources`  
\*\* Mempool plugin requires both TzKT and Tezos node endpoints to operate.
