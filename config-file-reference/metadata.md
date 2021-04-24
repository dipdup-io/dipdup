---
description: Plugins block
---

# metadata

This is an optional section used by the [metadata](https://github.com/dipdup-net/metadata) indexer plugin. It uses [`contracts`](contracts.md) and [`datasources`](datasources.md) aliases as well as the [`database`](database.md) connection.

Metadata configuration has two required sections: `settings` and `indexers`

{% page-ref page="../advanced/metadata-plugin.md" %}

## Settings

```yaml
metadata:
  settings:
    ipfs_gateways:
      - https://cloudflare-ipfs.com
    ipfs_timeout: 10
    http_timeout: 10
    max_retry_count_on_error: 3
  indexers:
    ...
```

#### ipfs\_gateways

An array of IPFS gateways. The indexer polls them sequentially until it gets a result or runs out of attempts. It is recommended to specify more than one gateway to overcome propagation issues, rate limits, and other problems.

#### ipfs\_timeout

How long DipDup will wait for a single IPFS gateway response. Default value is **10 seconds**.

#### http\_timeout

How long DipDup will wait for a HTTP server response. Default value is **10 seconds**.

#### max\_retry\_count\_on\_error

If DipDup fails to get a response from IPFS gateway or HTTP server, it will try again after some time, until it runs out of attempts. Default value is **3 attempts**.

## Indexers





