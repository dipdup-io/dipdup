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

.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktBigMapAction
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktBigMapData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktBigMapDiff
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktBlockData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktEvent
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktEventData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktHeadBlockData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktOperationData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktOperationType
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktOrigination
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktQuoteData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktSmartRollupCommitment
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktSmartRollupExecute
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktTokenBalanceData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktTokenStandard
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktTokenTransferData
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktTransaction
.. autoclass:: dipdup.models.tezos_tzkt.TezosTzktUnknownEvent

-------------------------------------------------------------------------------
Other
-------------------------------------------------------------------------------

.. autoclass:: dipdup.models.coinbase.CoinbaseCandleData
.. autoclass:: dipdup.models.coinbase.CoinbaseCandleInterval
.. autoclass:: dipdup.models.tzip_metadata.TzipMetadataNetwork