# datasources

A list of API endpoints DipDup uses to retrieve data and pass it to your indexer handlers. The obligatory field `kind` specifies which data adapter is to be used:

* `tzkt`
* `bcd`
* `tezos-node`
* `coinbase`
* `metadata`
* `ipfs`

## Datasources

### TzKT 😸

[TzKT](https://api.tzkt.io/) provides REST endpoints to query historical data and SignalR (Websocket) subscriptions to get realtime updates. Flexible filters allow you to request only data needed for your application and drastically speed up the indexing process.

```yaml
datasources:
  tzkt_mainnet:
    kind: tzkt
    url: https://api.tzkt.io
```

A datasource config entry is an alias for the endpoint URI; there's no network mention. Thus it's good to add a network name to the datasource alias. The reason behind this design choice is to provide a generic index parameterization via a single mechanism. See [4.5. Templates and variables](../getting-started/templates-and-variables.md) for details.

### Better Call Dev

> ⚠ **WARNING**
>
> Better Call Dev API is deprecated. Use `metadata` datasource instead.

Better Call Dev is another blockchain explorer and API with functionality similar to TzKT. It can't be used as a datasource for indexer and mempool/metadata plugins, but you can call it from inside of handlers to gather additional data.

```yaml
datasources:
  bcd_mainnet:
    kind: bcd
    url: https://api.better-call.dev
    network: mainnet

```

### Tezos node

Tezos RPC is a standard interface provided by the Tezos node. It's not suitable for indexing purposes but used for accessing mempool data and other things that are not available through TzKT.

```yaml
datasources:
  tezos_node_mainnet:
    kind: tezos-node
    url: https://mainnet-tezos.giganode.io
```

### Coinbase

A connector for [Coinbase Pro API](https://docs.pro.coinbase.com/). Provides `get_candles` and `get_oracle_data` methods. It may be useful in enriching indexes of DeFi contracts with off-chain data.

```yaml
datasources:
  coinbase:
    kind: coinbase
```

Please note that Coinbase can't replace TzKT being an index datasource. But you can access it via `ctx.datasources` mapping both within handler and job callbacks.

### dipdup-metadata

[dipdup-metadata](https://github.com/dipdup-net/metadata) is a standalone companion indexer for DipDup written in Go. Configure datasource in the following way:

```yaml
datasources:
  metadata:
    kind: metadata
    url: https://metadata.dipdup.net
    network: mainnet|handzhounet
```

### IPFS

While working with contract/token metadata, a typical scenario is to fetch it from IPFS. DipDup now has a separate datasource to perform such requests.

```yaml
datasources:
  ipfs:
    kind: ipfs
    url: https://ipfs.io/ipfs
```

You can use this datasource within any callback. Output is either JSON or binary data.

```python
ipfs = ctx.get_ipfs_datasource('ipfs')

file = await ipfs.get('QmdCz7XGkBtd5DFmpDPDN3KFRmpkQHJsDgGiG16cgVbUYu')
assert file[:4].decode()[1:] == 'PDF'

file = await ipfs.get('QmSgSC7geYH3Ae4SpUHy4KutxqNH9ESKBGXoCN4JQdbtEz/package.json')
assert file['name'] == 'json-buffer'
```

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

Each datasource has its defaults. Usually, there's no reason to alter these settings unless you use self-hosted instances of TzKT or BCD.

By default, DipDup retries failed requests infinitely exponentially increasing delay between attempts. Set `retry_count` parameter to limit the number of attempts.

`batch_size` parameter is TzKT-specific. By default, DipDup limit requests to 10000 items, the maximum value allowed on public instances provided by Baking Bad. Decreasing this value will reduce the time required for TzKT to process a single request and thus reduce the load. You can achieve the same effect (but limited to synchronizing multiple indexes concurrently) by reducing `connection_limit` parameter.

## Sending arbitrary requests

DipDup datasources do not cover all available methods of underlying APIs. Let's say you want to fetch protocol of the chain you're currently indexing from TzKT:

```python
tzkt = ctx.get_tzkt_datasource('tzkt_mainnet')
protocol_json = await tzkt.request(
    method='get',
    url='v1/protocols/current',
    cache=False,
    weigth=1,  # ratelimiter leaky-bucket drops
)
assert protocol_json['hash'] == 'PtHangz2aRngywmSRGGvrcTyMbbdpWdpFKuS4uMWxg2RaH9i1qx'
```

Datasource HTTP connection parameters (ratelimit, backoff, etc.) are applied on every request.
