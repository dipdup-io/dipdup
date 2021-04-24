---
description: Plugins block
---

# mempool

This is an optional section used by the [mempool](https://github.com/dipdup-net/mempool) indexer plugin. It uses [`contracts`](contracts.md) and [`datasources`](datasources.md) aliases as well as the [`database`](database.md) connection.

```yaml
mempool:
  settings:
    keep_operations_seconds: 172800
    expired_after_blocks: 60
    keep_in_chain_blocks: 10
    mempool_request_interval_seconds: 10
    rpc_timeout_seconds: 10
  indexers:
    mainnet:
      filters:
        kinds:
          - transaction
        accounts:
          - myaccount
      datasources:
          tzkt: tzkt_mainnet
          rpc: 
            - node_mainnet
```

{% page-ref page="../advanced/mempool-plugin.md" %}

## Settings

#### keep\_operations\_seconds

How long to store operations that did not get into the chain. After that period such operations will be wiped from the database. Default value is **172800** **seconds** \(2 days\).

#### expired\_after\_blocks

When `level(head) - level(operation.branch) >= expired_after_blocks` and operation is still on in chain it's marked as expired. Default value is **60 blocks** \(~1 hour\).

#### keep\_in\_chain\_blocks

Since the main purpose of this plugin is to index mempool operations \(actually it's a rolling index\), all the operations that were included in the chain are removed from the database after specified period of time. Default value is **10 blocks** \(~10 minutes\).

#### mempool\_request\_interval\_seconds

How often Tezos nodes should be polled for pending mempool operations. Default value is **10 seconds**.

#### rpc\_timeout\_seconds

Tezos node request timeout. Default value is **10 seconds**.

## Indexers

This section is used to create custom mempool indexers. You can create 1 indexer per network. Network is the primary key of indexer. For example:

```yaml
 indexers:
    mainnet:
    edonet:
    florencenet:
    
```

Every indexer has 2 settings: `filters` and `datasources`.

`filters` is the your filtration rules.

* `kinds` - array of mempool operation's kinds. It may be any of `activate_account`, `ballot`, `delegation`, `double_baking_evidence`, `double_endorsement_evidence`, `endorsement`, `origination`, `proposal`, `reveal`, `seed_nonce_revelation`, `transaction` Default: `transaction`.
* `accounts` - array of tezos tz and KT addresses which will be used for filtering by source, destination and etc.

`datasources` is section for setting URLs of tezos nodes and TzKT.

* `tzkt` - TzKT url
* `rpc` - array of tezos nodes URL.

