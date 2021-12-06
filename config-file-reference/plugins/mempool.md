---
description: Plugins block
---

# mempool

This is an optional section used by the [mempool](https://github.com/dipdup-net/mempool) indexer plugin. It uses [`contracts`](../contracts.md) and [`datasources`](../datasources.md) aliases as well as the [`database`](../database.md) connection.

Mempool configuration has two sections: `settings` and `indexers` (required).

{% content-ref url="../../advanced/mempool-plugin.md" %}
[mempool-plugin.md](../../advanced/mempool-plugin.md)
{% endcontent-ref %}

## Settings

This section is optional so are all the setting keys.

```yaml
mempool:
  settings:
    keep_operations_seconds: 172800
    expired_after_blocks: 60
    keep_in_chain_blocks: 10
    gas_stats_lifetime: 3600
  indexers:
    ...
```

#### keep\_operations\_seconds

How long to store operations that did not get into the chain. After that period such operations will be wiped from the database. Default value is **172800** **seconds** (2 days).

#### expired\_after\_blocks

When `level(head) - level(operation.branch) >= expired_after_blocks` and operation is still on in chain it's marked as expired. Default value is **60 blocks** (\~1 hour).

#### keep\_in\_chain\_blocks

Since the main purpose of this plugin is to index mempool operations (actually it's a rolling index), all the operations that were included in the chain are removed from the database after specified period of time. Default value is **10 blocks** (\~10 minutes).

**gas\_stats\_lifetime**

How long to store gas stats for operations. After that period such stats will be wiped from the database. Default value is **3600** **seconds** (1 hour).

## Indexers

You can index several networks at once, or index different nodes independently. Indexer names are not standardized, but for clarity it's better to stick with some meaningful keys:

```yaml
 mempool:
   settings:
     ...
   indexers:
     mainnet:
       filters:
         kinds:
           - transaction
         accounts:
           - contract_alias
       datasources:
         tzkt: tzkt_mainnet
         rpc: 
           - node_mainnet
     edonet:
     florencenet: 
```

Each indexer object has two keys: `filters` and `datasources` (required).

### Filters

An optional section specifying which mempool operations should be indexed. By default all transactions will be indexed.

#### kinds

Array of operations kinds, default value is `transaction` (single item).\
The complete list of values allowed:

* `activate_account`
* `ballot`
* `delegation*`
* `double_baking_evidence`
* `double_endorsement_evidence`
* `endorsement`
* `origination*`
* `proposal`
* `reveal*`
* `seed_nonce_revelation`
* `transaction*`
* `register_global_constant`

`*`  — manager operations.

#### accounts

Array of [contract](../contracts.md) aliases used to filter operations by source or destination.\
**NOTE**: applied to manager operations only.

### Datasources

Mempool plugin is tightly coupled with [TzKT](../datasources.md#tzkt) and [Tezos node](../datasources.md#tezos-node) providers.

#### tzkt

An alias pointing to a [datasource](../datasources.md) of kind `tzkt` is expected.

#### rpc

An array of aliases pointing to [datasources](../datasources.md) of kind `tezos-node`\
Polling multiple nodes allows to detect more refused operations and makes indexing more robust in general.
