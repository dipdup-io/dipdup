# Indexes

Index is a primary DipDup entity connecting the inventory and data handling rules.

Multiple indexes are available for different workloads. Every index is linked to a specific datasource and provides a set of handlers for different kinds of data. Use this table to choose the right index for the task:

| kind                                                       | blockchain     | datasource | indexed data                |
| ---------------------------------------------------------- | -------------- | ---------- | --------------------------- |
| {{ #summary indexes/evm_subsquid_events.md }}              | EVM-compatible | Subsquid   | event logs                  |
| {{ #summary indexes/tezos_tzkt_big_maps.md }}              | Tezos          | TzKT       | big map diffs               |
| {{ #summary indexes/tezos_tzkt_events.md }}                | Tezos          | TzKT       | events                      |
| {{ #summary indexes/tezos_tzkt_head.md }}                  | Tezos          | TzKT       | head blocks (realtime only) |
| {{ #summary indexes/tezos_tzkt_operations.md }}            | Tezos          | TzKT       | typed operations            |
| {{ #summary indexes/tezos_tzkt_operations_unfiltered.md }} | Tezos          | TzKT       | untyped operations          |
| {{ #summary indexes/tezos_tzkt_token_transfers.md }}       | Tezos          | TzKT       | TZIP-12/16 token transfers  |

Indexes can join multiple contracts considered as a single application. Also, contracts can be used by multiple indexes of any kind, but make sure that they are independent of each other and indexed data don't overlap. Make sure to visit {{ #summary getting-started/core-concepts.md#atomicity-and-persistency }}.

Handler is a callback function, called when new data has arrived from the datasource. The handler receives the data item as an argument and can perform any actions, e.g., store data in the database, send a notification, or call an external API.

## Using templates

Index definitions can be templated to reduce the amount of boilerplate code. To create an index from template use the following syntax:

```yaml
templates:
  operation_index_template:
    kind: tezos.tzkt.operations
    datasource: <datasource>
    ...

indexes:
  template_instance:
    template: operation_index_template
    values:
      datasource: tzkt_mainnet
```

You can also spawn indexes from templates in runtime; see {{ #summary getting-started/templates-and-variables.md }} page.

## Indexing scope

One can optionally specify block levels DipDup has to start and stop indexing at, e.g., there's a new version of the contract, and there's no need to track the old one anymore.

```yaml
indexes:
  my_index:
    first_level: 1000000
    last_level: 2000000
```
