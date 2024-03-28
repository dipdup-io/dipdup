import random
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import cast

from web3 import Web3

from dipdup.config import SubsquidIndexConfigU
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.context import DipDupContext
from dipdup.datasources import IndexDatasource
from dipdup.datasources.evm_node import NODE_LAST_MILE
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import IndexQueueItemT
from dipdup.models.evm_subsquid import SubsquidMessageType
from dipdup.package import DipDupPackage
from dipdup.prometheus import Metrics

SUBSQUID_READAHEAD_LIMIT = 10000

IndexConfigT = TypeVar('IndexConfigT', bound=SubsquidIndexConfigU)
DatasourceT = TypeVar('DatasourceT', bound=SubsquidDatasource)


_sighashes: dict[str, str] = {}


def get_sighash(package: DipDupPackage, method: str, to: EvmContractConfig | None = None) -> str:
    """Method in config is either a full signature or a method name. We need to convert it to a sighash first."""
    key = method + (to.module_name if to else '')
    if key in _sighashes:
        return _sighashes[key]

    if {'(', ')'} <= set(method) and not to:
        _sighashes[key] = Web3.keccak(text=method).hex()[:10]
    elif to:
        _sighashes[key] = package.get_converted_abi(to.module_name)['methods'][method]['sighash']
    else:
        raise ConfigurationError('`to` field is missing; `method` is expected to be a full signature')
    return _sighashes[key]


class SubsquidIndex(
    Generic[IndexConfigT, IndexQueueItemT, DatasourceT],
    Index[IndexConfigT, IndexQueueItemT, DatasourceT],
    ABC,
    message_type=SubsquidMessageType,  # type: ignore[arg-type]
):
    def __init__(
        self,
        ctx: DipDupContext,
        config: IndexConfigT,
        datasource: DatasourceT,
    ) -> None:
        super().__init__(ctx, config, datasource)

        node_field = self._config.datasource.node
        if node_field is None:
            node_field = ()
        elif isinstance(node_field, EvmNodeDatasourceConfig):
            node_field = (node_field,)
        self._node_datasources = tuple(
            self._ctx.get_evm_node_datasource(node_config.name) for node_config in node_field
        )

    @abstractmethod
    async def _synchronize_subsquid(self, sync_level: int) -> None: ...

    @abstractmethod
    async def _synchronize_node(self, sync_level: int) -> None: ...

    @property
    def node_datasources(self) -> tuple[EvmNodeDatasource, ...]:
        return self._node_datasources

    @property
    def datasources(self) -> tuple[IndexDatasource[Any], ...]:
        return (self.datasource, *self.node_datasources)

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

    async def _get_node_sync_level(
        self,
        subsquid_level: int,
        index_level: int,
        node: EvmNodeDatasource | None = None,
    ) -> int | None:
        if not self.node_datasources:
            return None
        node = node or random.choice(self.node_datasources)

        node_sync_level = await node.get_head_level()
        subsquid_lag = abs(node_sync_level - subsquid_level)
        subsquid_available = subsquid_level - index_level
        self._logger.info('Subsquid is %s levels behind; %s available', subsquid_lag, subsquid_available)
        if subsquid_available < NODE_LAST_MILE:
            return node_sync_level
        if self._config.node_only:
            self._logger.debug('`node_only` flag is set; using node anyway')
            return node_sync_level
        return None

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch event logs via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        levels_left = sync_level - index_level
        if levels_left <= 0:
            return

        subsquid_sync_level = await self.datasource.get_head_level()
        Metrics.set_sqd_processor_chain_height(subsquid_sync_level)
        node_sync_level = await self._get_node_sync_level(subsquid_sync_level, index_level)

        # NOTE: Fetch last blocks from node if there are not enough realtime messages in queue
        if node_sync_level:
            sync_level = min(sync_level, node_sync_level)
            self._logger.debug('Using node datasource; sync level: %s', sync_level)
            await self._synchronize_node(sync_level)
        else:
            sync_level = min(sync_level, subsquid_sync_level)
            await self._synchronize_subsquid(sync_level)

        await self._exit_sync_state(sync_level)
