# datasources

A list of API endpoints DipDup uses to retrieve indexing data to process.

A datasource config entry is an alias for the endpoint URI; there's no network mention. Thus it's good to add a network name to the datasource alias, e.g. `tzkt_mainnet`.

## TzKT

```yaml
datasources:
  tzkt:
    kind: tzkt
    url: ${TZKT_URL:-https://api.tzkt.io}
```

| field | description |
| - | - |
| `kind` | always 'tzkt' |
| `url` | Base API URL, e.g. https://api.tzkt.io/ |
| `http` | HTTP client configuration |

-------------------------

 See [4.5. Templates and variables](../getting-started/templates-and-variables.md) for details.

### TzKT

[TzKT](https://api.tzkt.io/) provides REST endpoints to query historical data and SignalR (Websocket) subscriptions to get realtime updates. Flexible filters allow you to request only data needed for your application and drastically speed up the indexing process.

```yaml
datasources:
  tzkt_mainnet:
    kind: tzkt
    url: https://api.tzkt.io
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
