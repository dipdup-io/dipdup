import logging

from dipdup.exceptions import MigrationError
from dipdup.migrations import ProjectMigration
from dipdup.yaml import DipDupYAMLConfig

INDEX_KINDS = {
    'evm.subsquid.events': 'evm.events',
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
