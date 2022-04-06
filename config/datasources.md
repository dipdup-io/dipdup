# datasources

A list of API endpoints DipDup uses to retrieve indexing data to process.

A datasource config entry is an alias for the endpoint URI; there's no network mention. Thus it's good to add a network name to the datasource alias, e.g. `tzkt_mainnet`.

## tzkt

```yaml
datasources:
  tzkt:
    kind: tzkt
    url: ${TZKT_URL:-https://api.tzkt.io}
```

## coinbase

```yaml
datasources:
  coinbase:
    kind: coinbase
```

## dipdup-metadata

```yaml
datasources:
  metadata:
    kind: metadata
    url: https://metadata.dipdup.net
    network: mainnet|handzhounet
```

## ipfs

```yaml
datasources:
  ipfs:
    kind: ipfs
    url: https://ipfs.io/ipfs
```

> 🤓 **SEE ALSO**
>
> * [5.1. datasources](../advanced/datasources.md)
