<!-- markdownlint-disable first-line-h1 -->
## Using EVM node

DipDup indexes for EVM networks use [Subsquid Network](https://docs.subsquid.io/subsquid-network/overview/) as a source of historical data. EVM nodes are not required for DipDup to operate, but they can be used to get the latest data (not yet in Subsquid Network) and realtime updates. See [evm.subsquid](../3.datasources/4.evm_subsquid.md) and [evm.node](../3.datasources/3.evm_node.md) pages for more info on how to configure both datasources.

For testing purposes, you can enforce DipDup to use only data from EVM node.

```yaml [dipdup.yaml]
indexes:
  evm_index:
    kind: evm.<index>
    datasources:
      - evm_node
```
