# Datasources

Datasources are DipDup connectors to various APIs. The table below shows how different datasources can be used.

**Index** datasource is the one used by DipDup internally to process specific index (set with `datasource: ...` in config). Currently, it can be only `tzkt`. Datasources available in **context** can be accessed in handlers and hooks via `ctx.get_<kind>_datasource()` methods and used to perform arbitrary requests. Finally, **standalone services** implement a subset of DipDup datasources and config directives. You can't use services-specific datasources like `tezos-node` in the main framework, they are here for informational purposes only.

|              | index | context | `mempool` service | `metadata` service |
| :----------- | :---: | :-----: | :---------------: | :----------------: |
| `tzkt`       |   ✴   |    ✅    |         ✴         |         ✴          |
| `tezos-node` |   ❌   |    ❌    |         ✴         |         ❌          |
| `coinbase`   |   ❌   |    ✅    |         ❌         |         ❌          |
| `metadata`   |   ❌   |    ✅    |         ❌         |         ❌          |
| `ipfs`       |   ❌   |    ✅    |         ❌         |         ❌          |
| `http`       |   ❌   |    ✅    |         ❌         |         ❌          |

✴ *required* ✅ *supported* ❌ *not supported*

## TzKT

[TzKT](https://api.tzkt.io/) provides REST endpoints to query historical data and SignalR (Websocket) subscriptions to get realtime updates. Flexible filters allow you to request only data needed for your application and drastically speed up the indexing process.

```yaml
datasources:
  tzkt_mainnet:
    kind: tzkt
    url: https://api.tzkt.io
```

The number of items in each request can be configured with `batch_size` directive. Affects request number and memory usage.

```yaml
datasources:
  tzkt_mainnet:
    http:
      ...
      batch_size: 10000
```

The rest HTTP tunables are the same as for other datasources.

Also, you can wait for several block confirmations before processing the operations:

```yaml
datasources:
  tzkt_mainnet:
    ...
    buffer_size: 1  # indexing with a single block lag
```

Since 6.0 chain reorgs are processed automatically, but you may find this feature useful for other cases.

## Tezos node

Tezos RPC is a standard interface provided by the Tezos node. This datasource is used solely by `mempool` and `metadata` standalone services; you can't use it in regular DipDup indexes.

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
    network: mainnet | ithacanet
```

Then, in your hook or handler code:

```python
datasource = ctx.get_metadata_datasource('metadata')
token_metadata = await datasource.get_token_metadata('KT1...', '0')
```

## IPFS

While working with contract/token metadata, a typical scenario is to fetch it from IPFS. DipDup has a separate datasource to perform such requests via public nodes.

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

## HTTP (generic)

If you need to perform arbitrary requests to APIs not supported by DipDup, use generic HTTP datasource instead of plain `aiohttp` requests. That way you can use the same features DipDup uses for internal requests: retry with backoff, rate limiting, Prometheus integration etc.

```yaml
datasources:
  my_api:
    kind: http
    url: https://my_api.local/v1
```

```python
api = ctx.get_http_datasource('my_api')
response = await api.request(
    method='get',
    url='hello',  # relative to URL in config
    weigth=1,  # ratelimiter leaky-bucket drops
    params={
      'foo': 'bar',
    },
)
```

All DipDup datasources are inherited from `http`, so you can send arbitrary requests with any datasource. Let's say you want to fetch the protocol of the chain you're currently indexing (`tzkt` datasource doesn't have a separate method for it):

```python
tzkt = ctx.get_tzkt_datasource('tzkt_mainnet')
protocol_json = await tzkt.request(
    method='get',
    url='v1/protocols/current',
)
assert protocol_json['hash'] == 'PtHangz2aRngywmSRGGvrcTyMbbdpWdpFKuS4uMWxg2RaH9i1qx'
```

Datasource HTTP connection parameters (ratelimit, retry with backoff, etc.) are applied on every request.

> 💡 **SEE ALSO**
>
> * {{ #summary config/datasources.md}}
