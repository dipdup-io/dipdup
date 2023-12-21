import random
from abc import ABC
from typing import Generic
from typing import TypeVar
from typing import cast

from dipdup.config import SubsquidIndexConfigU
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.context import DipDupContext
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import IndexQueueItemT
from dipdup.models.evm_subsquid import SubsquidMessageType

IndexConfigT = TypeVar('IndexConfigT', bound=SubsquidIndexConfigU)
DatasourceT = TypeVar('DatasourceT', bound=SubsquidDatasource)


class SubsquidIndex(
    Index[IndexConfigT, IndexQueueItemT, DatasourceT],
    ABC,
    Generic[IndexConfigT, IndexQueueItemT, DatasourceT],
    message_type=SubsquidMessageType,
):
    def __init__(
        self,
        ctx: DipDupContext,
        config: IndexConfigT,
        datasource: DatasourceT,
    ) -> None:
        super().__init__(ctx, config, datasource)
        self._realtime_node: EvmNodeDatasource | None = None

        node_field = self._config.datasource.node
        if node_field is None:
            node_field = ()
        elif isinstance(node_field, EvmNodeDatasourceConfig):
            node_field = (node_field,)
        self._node_datasources = tuple(
            self._ctx.get_evm_node_datasource(node_config.name) for node_config in node_field
        )

    @property
    def node_datasources(self) -> tuple[EvmNodeDatasource, ...]:
        return self._node_datasources

    def get_random_node(self) -> EvmNodeDatasource:
        if not self._node_datasources:
            raise FrameworkException('A node datasource requested, but none attached to this index')
        return random.choice(self._node_datasources)

    def get_realtime_node(self) -> EvmNodeDatasource:
        if self._realtime_node is None:
            self._realtime_node = self.get_random_node()
            self._realtime_node.use_realtime()
        return self._realtime_node

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        sync_levels = set()
        for sub in self._config.get_subscriptions():
            sync_levels.add(self.datasource.get_sync_level(sub))
            for datasource in self.node_datasources or ():
                sync_levels.add(datasource.get_sync_level(sub))

        if None in sync_levels:
            sync_levels.remove(None)
        if not sync_levels:
            raise FrameworkException('Initialize config before starting `IndexDispatcher`')

        # NOTE: Multiple sync levels means index with new subscriptions was added in runtime.
        # NOTE: Choose the highest level; outdated realtime messages will be dropped from the queue anyway.
        return max(cast(set[int], sync_levels))
