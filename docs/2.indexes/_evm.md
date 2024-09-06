<!-- markdownlint-disable first-line-h1 -->
## Datasources

DipDup indexes for EVM networks use [Subsquid Network](https://docs.subsquid.io/subsquid-network/overview/) as a main source of historical data. EVM nodes are not required for DipDup to operate, but they can be used to get the latest data (not yet in Subsquid Network) and realtime updates. See [evm.subsquid](../3.datasources/4.evm_subsquid.md) and [evm.node](../3.datasources/2.evm_node.md) pages for more info on how to configure both datasources.

For testing purposes, you can use EVM node as a single datasource, but indexing will be significantly slower. For production, it's recommended to use Subsquid Network as the main datasource and EVM node(s) as a secondary one. If there are multiple `evm.node` datasources attached to index, DipDup will use random one for each request.
