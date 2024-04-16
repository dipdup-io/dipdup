:orphan:

===============================================================================
Base classes
===============================================================================

.. autoclass:: dipdup.models.CachedModel
.. autoclass:: dipdup.models.Model

===============================================================================
Internal models
===============================================================================

.. autoclass:: dipdup.models.ContractMetadata
.. autoclass:: dipdup.models.Head
.. autoclass:: dipdup.models.TokenMetadata
.. autoclass:: dipdup.models.Contract
.. autoclass:: dipdup.models.ContractKind
.. autoclass:: dipdup.models.Index
.. autoclass:: dipdup.models.IndexStatus
.. autoclass:: dipdup.models.IndexType
.. autoclass:: dipdup.models.Schema
.. autoclass:: dipdup.models.ReindexingAction
.. autoclass:: dipdup.models.ReindexingReason
.. autoclass:: dipdup.models.SkipHistory
.. autoclass:: dipdup.models.Meta
.. autoclass:: dipdup.models.ModelUpdate
.. autoclass:: dipdup.models.ModelUpdateAction


===============================================================================
Datasource models
===============================================================================

-------------------------------------------------------------------------------
EVM
-------------------------------------------------------------------------------

.. autoclass:: dipdup.models.evm.EvmTransaction
.. autoclass:: dipdup.models.evm.EvmTransactionData
.. autoclass:: dipdup.models.evm.EvmLog
.. autoclass:: dipdup.models.evm.EvmLogData
.. autoclass:: dipdup.models.evm_node.EvmNodeHeadData
.. autoclass:: dipdup.models.evm_node.EvmNodeSyncingData

-------------------------------------------------------------------------------
Tezos
-------------------------------------------------------------------------------

.. autoclass:: dipdup.models.tezos_tzkt.TezosBigMapAction
.. autoclass:: dipdup.models.tezos_tzkt.TezosBigMapData
.. autoclass:: dipdup.models.tezos_tzkt.TezosBigMapDiff
.. autoclass:: dipdup.models.tezos_tzkt.TezosBlockData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktEvent
.. autoclass:: dipdup.models.tezos_tzkt.TezosEventData
.. autoclass:: dipdup.models.tezos_tzkt.TezosHeadBlockData
.. autoclass:: dipdup.models.tezos_tzkt.TezosOperationData
.. autoclass:: dipdup.models.tezos_tzkt.TezosOperationType
.. autoclass:: dipdup.models.tezos_tzkt.TezosOrigination
.. autoclass:: dipdup.models.tezos_tzkt.TezosQuoteData
.. autoclass:: dipdup.models.tezos_tzkt.TezosSmartRollupCommitment
.. autoclass:: dipdup.models.tezos_tzkt.TezosSmartRollupExecute
.. autoclass:: dipdup.models.tezos_tzkt.TezosTokenBalanceData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTokenStandard
.. autoclass:: dipdup.models.tezos_tzkt.TezosTokenTransferData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTransaction
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktUnknownEvent

-------------------------------------------------------------------------------
Other
-------------------------------------------------------------------------------

.. autoclass:: dipdup.models.coinbase.CoinbaseCandleData
.. autoclass:: dipdup.models.coinbase.CoinbaseCandleInterval
.. autoclass:: dipdup.models.tzip_metadata.TzipMetadataNetwork