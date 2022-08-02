# Datasources

Datasources are DipDup connectors to various APIs. TzKT data is used for indexing, other sources are complimentary.

|  | `tzkt` | `tezos-node` | `coinbase` | `metadata` | `ipfs` | `http` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Callback context (via `ctx.datasources`) | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| DipDup index | ✅\* | ❌ | ❌ | ❌ | ❌ | ❌ |
| `mempool` service | ✅\* | ✅\* | ❌ | ❌ | ❌ | ❌ |
| `metadata` service | ✅\* | ❌ | ❌ | ❌ | ❌ | ❌ |

\* - required

## TzKT

[TzKT](https://api.tzkt.io/) provides REST endpoints to query historical data and SignalR (Websocket) subscriptions to get realtime updates. Flexible filters allow you to request only data needed for your application and drastically speed up the indexing process.

```yaml
datasources:
  tzkt_mainnet:
    kind: tzkt
    url: https://api.tzkt.io
```

TzKT datasource is based on generic HTTP datasource and thus inherits its settings (optional):

```yaml
datasources:
  tzkt_mainnet:
    http:
      retry_count:  # retry infinetely
      retry_sleep:
      retry_multiplier:
      ratelimit_rate:
      ratelimit_period:
      connection_limit: 100
      connection_timeout: 60
      batch_size: 10000
```

Also you can wait for several block confirmations before processing the operations, e.g. to mitigate chain reorgs:

```yaml
datasources:
  tzkt_mainnet:
    buffer_size: 1  # indexing with single block lag
```

## Tezos node

Tezos RPC is a standard interface provided by the Tezos node. It's not suitable for indexing purposes but used for accessing mempool data and other things that are not available through TzKT.

```yaml
datasources:
  tezos_node_mainnet:
    kind: tezos-node
    url: https://mainnet-tezos.giganode.io
```

## Coinbase

A connector for [Coinbase Pro API](https://docs.pro.coinbase.com/). Provides `get_candles` and `get_oracle_data` methods. It may be useful in enriching indexes of DeFi contracts with off-chain data.

```yaml
datasources:
  coinbase:
    kind: coinbase
```

Please note that Coinbase can't replace TzKT being an index datasource. But you can access it via `ctx.datasources` mapping both within handler and job callbacks.

## DipDup Metadata

[dipdup-metadata](https://github.com/dipdup-net/metadata) is a standalone companion indexer for DipDup written in Go. Configure datasource in the following way:

```yaml
datasources:
  metadata:
    kind: metadata
    url: https://metadata.dipdup.net
    network: mainnet|handzhounet
```

## IPFS

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

## Sending arbitrary requests

DipDup datasources do not cover all available methods of underlying APIs. Let's say you want to fetch protocol of the chain you're currently indexing from TzKT:

```python
tzkt = ctx.get_tzkt_datasource('tzkt_mainnet')
protocol_json = await tzkt.request(
    method='get',
    url='v1/protocols/current',
    weigth=1,  # ratelimiter leaky-bucket drops
)
assert protocol_json['hash'] == 'PtHangz2aRngywmSRGGvrcTyMbbdpWdpFKuS4uMWxg2RaH9i1qx'
```

Datasource HTTP connection parameters (ratelimit, backoff, etc.) are applied on every request.

> 💡 **SEE ALSO**
>
> * {{ #summary config/datasources.md}}
