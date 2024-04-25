import logging

from dipdup.exceptions import MigrationError
from dipdup.migrations import ProjectMigration
from dipdup.yaml import DipDupYAMLConfig

# IMPORTS = {
#     'dipdup.config.evm_subsquid_events.SubsquidEventsHandlerConfig': 'dipdup.config.evm_logs.EvmLogsHandlerConfig',
#     'dipdup.config.evm_subsquid_events.SubsquidEventsIndexConfig': 'dipdup.config.evm_logs.EvmLogsIndexConfig',
#     'dipdup.config.evm_subsquid.SubsquidDatasourceConfig': 'dipdup.config.evm_subsquid.EvmSubsquidDatasourceConfig',
#     'dipdup.config.evm_subsquid.EvmIndexConfig': 'dipdup.config.evm_subsquid.EvmIndexConfig',
#     'dipdup.config.evm_subsquid_transactions.SubsquidTransactionsHandlerConfig': 'dipdup.config.evm_subsquid_transactions.EvmTransactionsHandlerConfig',
#     'dipdup.config.tezos_tzkt_big_maps.TzktBigMapsHandlerConfig': 'dipdup.config.tezos_tzkt_big_maps.TezosTzktBigMapsHandlerConfig',
#     'dipdup.config.tezos_tzkt_big_maps.TzktBigMapsIndexConfig': 'dipdup.config.tezos_tzkt_big_maps.TezosTzktBigMapsIndexConfig',
#     'dipdup.config.tezos_tzkt_events.TzktEventsHandlerConfig': 'dipdup.config.tezos_tzkt_events.TezosTzktEventsHandlerConfig',
#     'dipdup.config.tezos_tzkt_events.TzktEventsIndexConfig': 'dipdup.config.tezos_tzkt_events.TezosTzktEventsIndexConfig',
#     'dipdup.config.tezos_tzkt_events.TzktEventsUnknownEventHandlerConfig': 'dipdup.config.tezos_tzkt_events.TezosTzktEventsUnknownIndexHandlerConfig',
#     'dipdup.config.tezos_tzkt_head.TzktHeadHandlerConfig': 'dipdup.config.tezos_tzkt_head.TezosTzktHeadHandlerConfig',
#     'dipdup.config.tezos_tzkt_head.TzktHeadIndexConfig': 'dipdup.config.tezos_tzkt_head.TezosTzktHeadIndexConfig',
#     'dipdup.config.tezos_tzkt_operations.OperationsHandlerConfigU': 'dipdup.config.tezos_tzkt_operations.TezosOperationsHandlerConfigU',
#     'dipdup.config.tezos_tzkt_operations.OperationsHandlerOriginationPatternConfig': 'dipdup.config.tezos_tzkt_operations.TezosOperationsHandlerOriginationPatternConfig',
#     'dipdup.config.tezos_tzkt_operations.OperationsHandlerPatternConfigU': 'dipdup.config.tezos_tzkt_operations.TezosOperationsHandlerPatternConfigU',
#     'dipdup.config.tezos_tzkt_operations.OperationsHandlerSmartRollupExecutePatternConfig': 'dipdup.config.tezos_tzkt_operations.TezosOperationsHandlerSmartRollupExecutePatternConfig',
#     'dipdup.config.tezos_tzkt_operations.OperationsHandlerTransactionPatternConfig': 'dipdup.config.tezos_tzkt_operations.TezosOperationsHandlerTransactionPatternConfig',
#     'dipdup.config.tezos_tzkt_operations.OperationsIndexConfigU': 'dipdup.config.tezos_tzkt_operations.TezosOperationsIndexConfigU',
#     'dipdup.config.tezos_tzkt_operations.TzktOperationsHandlerConfig': 'dipdup.config.tezos_tzkt_operations.TezosOperationsHandlerConfig',
#     'dipdup.config.tezos_tzkt_operations.TzktOperationsIndexConfig': 'dipdup.config.tezos_tzkt_operations.TezosOperationsIndexConfig',
#     'dipdup.config.tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig': 'dipdup.config.tezos_tzkt_operations.TezosOperationsUnfilteredIndexConfig',
#     'dipdup.config.tezos_tzkt_token_balances.TzktTokenBalancesHandlerConfig': 'dipdup.config.tezos_tzkt_token_balances.TezosTzktTokenBalancesHandlerConfig',
#     'dipdup.config.tezos_tzkt_token_balances.TzktTokenBalancesIndexConfig': 'dipdup.config.tezos_tzkt_token_balances.TezosTzktTokenBalancesIndexConfig',
#     'dipdup.config.tezos_tzkt_token_transfers.TzktTokenTransfersHandlerConfig': 'dipdup.config.tezos_tzkt_token_transfers.TezosTzktTokenTransfersHandlerConfig',
#     'dipdup.config.tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig': 'dipdup.config.tezos_tzkt_token_transfers.TezosTzktTokenTransfersIndexConfig',
#     'dipdup.config.tezos_tzkt.TzktDatasourceConfig': 'dipdup.config.tezos_tzkt.TezosTzktDatasourceConfig',
#     'dipdup.config.tezos_tzkt.TzktIndexConfig': 'dipdup.config.tezos.TezosIndexConfig',
#     'dipdup.datasources.evm_subsquid.SubsquidDatasource': 'dipdup.datasources.evm_subsquid.EvmDatasource',
#     'dipdup.datasources.tezos_tzkt.TzktDatasource': 'dipdup.datasources.tezos_tzkt.TezosTzktDatasource',
#     'dipdup.models.coinbase.CandleData': 'dipdup.models.coinbase.CoinbaseCandleData',
#     'dipdup.models.coinbase.CandleInterval': 'dipdup.models.coinbase.CoinbaseCandleInterval',
#     'dipdup.models.evm_subsquid.SubsquidEventData': 'dipdup.models.evm_subsquid.EvmEventData',
#     'dipdup.models.evm_subsquid.SubsquidEvent': 'dipdup.models.evm_subsquid.EvmEvent',
#     'dipdup.models.evm_subsquid.SubsquidMessageType': 'dipdup.models.subsquid.SubsquidMessageType',
#     'dipdup.models.evm_subsquid.SubsquidTransactionData': 'dipdup.models.evm_subsquid.EvmTransactionData',
#     'dipdup.models.evm_subsquid.SubsquidTransaction': 'dipdup.models.evm_subsquid.EvmTransaction',
#     'dipdup.models.tezos_tzkt.TzktBigMapAction': 'dipdup.models.tezos.TezosBigMapAction',
#     'dipdup.models.tezos_tzkt.TzktBigMapData': 'dipdup.models.tezos.TezosBigMapData',
#     'dipdup.models.tezos_tzkt.TzktBigMapDiff': 'dipdup.models.tezos.TezosBigMapDiff',
#     'dipdup.models.tezos_tzkt.TzktBlockData': 'dipdup.models.tezos.TezosBlockData',
#     'dipdup.models.tezos_tzkt.TzktEventData': 'dipdup.models.tezos.TezosEventData',
#     'dipdup.models.tezos_tzkt.TzktEvent': 'dipdup.models.tezos.TezosEvent',
#     'dipdup.models.tezos_tzkt.TzktHeadBlockData': 'dipdup.models.tezos.TezosHeadBlockData',
#     'dipdup.models.tezos_tzkt.TzktMessageType': 'dipdup.models.tezos.TezosMessageType',
#     'dipdup.models.tezos_tzkt.TzktOperationData': 'dipdup.models.tezos.TezosOperationData',
#     'dipdup.models.tezos_tzkt.TzktOperationType': 'dipdup.models.tezos.TezosOperationType',
#     'dipdup.models.tezos_tzkt.TzktOrigination': 'dipdup.models.tezos.TezosOrigination',
#     'dipdup.models.tezos_tzkt.TzktQuoteData': 'dipdup.models.tezos.TezosQuoteData',
#     'dipdup.models.tezos_tzkt.TzktSmartRollupCommitment': 'dipdup.models.tezos.TezosSmartRollupCommitment',
#     'dipdup.models.tezos_tzkt.TzktSmartRollupExecute': 'dipdup.models.tezos.TezosSmartRollupExecute',
#     'dipdup.models.tezos_tzkt.TzktSubscription': 'dipdup.models.tezos_tzkt.TezosTzktSubscription',
#     'dipdup.models.tezos_tzkt.TzktTokenBalanceData': 'dipdup.models.tezos.TezosTokenBalanceData',
#     'dipdup.models.tezos_tzkt.TzktTokenStansard': 'dipdup.models.tezos.TezosTokenStandard',
#     'dipdup.models.tezos_tzkt.TzktTokenTransferData': 'dipdup.models.tezos.TezosTokenTransferData',
#     'dipdup.models.tezos_tzkt.TzktTokenTransfersHandlerConfig': 'dipdup.models.tezos.TezosTokenTransfersHandlerConfig',
#     'dipdup.models.tezos_tzkt.TzktUnknownEvent': 'dipdup.models.tezos.TezosUnknownEvent',
# }
# METHODS = {
#     'config.get_tzkt_datasource': 'config.get_tezos_tzkt_datasource',
#     'config.get_subsquid_datasource': 'config.get_evm_subsquid_datasource',
#     'ctx.get_subsquid_datasource': 'ctx.get_evm_subsquid_datasource',
#     'ctx.get_tzkt_datasource': 'ctx.get_tezos_tzkt_datasource',
# }

INDEX_KINDS = {
    'evm.subsquid.events': 'evm.logs',
    'evm.subsquid.transactions': 'evm.transactions',
    'tezos.tzkt.big_maps': 'tezos.big_maps',
    'tezos.tzkt.events': 'tezos.events',
    'tezos.tzkt.head': 'tezos.head',
    'tezos.tzkt.operations': 'tezos.operations',
    'tezos.tzkt.operations_unfiltered': 'tezos.operations_unfiltered',
    'tezos.tzkt.token_balances': 'tezos.token_balances',
    'tezos.tzkt.token_transfers': 'tezos.token_transfers',
}


_logger = logging.getLogger(__name__)


class ThreeZeroProjectMigration(ProjectMigration):
    from_spec = ('2.0',)
    to_spec = '3.0'

    def migrate_config(self, config: DipDupYAMLConfig) -> DipDupYAMLConfig:

        add_node = {}

        for alias, datasource in config.get('datasources', {}).items():
            if node := datasource.pop('node', None):
                if isinstance(node, str):
                    node = [node]
                add_node[alias] = node

        for section in ('indexes', 'templates'):
            for alias, index in config.get(section, {}).items():
                if 'template' in index:
                    continue
                if 'kind' not in index:
                    raise MigrationError(
                        f"{section}.{alias}: Can't determine index kind. Please specify `kind` field and try again."
                    )

                if index['kind'] in INDEX_KINDS:
                    index['kind'] = INDEX_KINDS[index['kind']]

                if 'datasource' in index:
                    index['datasources'] = [index.pop('datasource')]

                if 'abi' in index:
                    index['datasources'].append(index.pop('abi'))

                for ds_alias in index['datasources']:
                    if ds_alias in add_node:
                        index['datasources'].extend(add_node[ds_alias])

        config['spec_version'] = self.to_spec

        return config
