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
| `url` | Base API URL, e.g. <https://api.tzkt.io/> |
| `http` | HTTP client configuration |

-------------------------

 See [4.5. Templates and variables](../getting-started/templates-and-variables.md) for details.

### TzKT

### Coinbase

### dipdup-metadata

```yaml
datasources:
  metadata:
    kind: metadata
    url: https://metadata.dipdup.net
    network: mainnet|handzhounet
```

### IPFS
