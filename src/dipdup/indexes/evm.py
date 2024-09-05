import random
from abc import ABC
from abc import abstractmethod
from functools import cache
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar

from dipdup.config.evm import EvmContractConfig
from dipdup.datasources.evm_node import NODE_LAST_MILE
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.index import Index
from dipdup.index import IndexQueueItemT
from dipdup.package import DipDupPackage
from dipdup.prometheus import Metrics

if TYPE_CHECKING:
    from dipdup.context import DipDupContext


IndexConfigT = TypeVar('IndexConfigT', bound=Any)
DatasourceT = TypeVar('DatasourceT', bound=Any)


@cache
def get_sighash(
    package: DipDupPackage,
    method: str | None = None,
    signature: str | None = None,
    to: EvmContractConfig | None = None,
) -> str:
    """Method in config is either a full signature or a method name. We need to convert it to a sighash first."""

    if to and (method or signature):
        return package._evm_abis.get_method_abi(
            typename=to.module_name,
            name=method,
            signature=signature,
        )['sighash']

    if (not to) and signature:
        from web3 import Web3

        return '0x' + Web3.keccak(text=signature).hex()[:8]

    raise ConfigurationError('Either `to` or `signature` filters are expected')


class EvmIndex(
    Generic[IndexConfigT, IndexQueueItemT, DatasourceT],
    Index[IndexConfigT, IndexQueueItemT, DatasourceT],
    ABC,
):
    subsquid_datasources: tuple[Any, ...]
    node_datasources: tuple[Any, ...]

    def __init__(
        self,
        ctx: 'DipDupContext',
        config: IndexConfigT,
        datasources: tuple[DatasourceT, ...],
    ) -> None:
        super().__init__(ctx, config, datasources)
        self.subsquid_datasources = tuple(d for d in datasources if isinstance(d, EvmSubsquidDatasource))
        self.node_datasources = tuple(d for d in datasources if isinstance(d, EvmNodeDatasource))
        self._subsquid_started: bool = False
        self._abis = ctx.package._evm_abis

    @abstractmethod
    async def _synchronize_subsquid(self, sync_level: int) -> None: ...

    @abstractmethod
    async def _synchronize_node(self, sync_level: int) -> None: ...

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
        return None

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch event logs via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        levels_left = sync_level - index_level
        if levels_left <= 0:
            return

        if self.subsquid_datasources:
            subsquid_sync_level = await self.subsquid_datasources[0].get_head_level()
            Metrics.set_sqd_processor_chain_height(subsquid_sync_level)
        else:
            subsquid_sync_level = 0

        node_sync_level = await self._get_node_sync_level(subsquid_sync_level, index_level)

        # NOTE: Fetch last blocks from node if there are not enough realtime messages in queue
        if node_sync_level:
            sync_level = min(sync_level, node_sync_level)
            self._logger.debug('Using node datasource; sync level: %s', sync_level)
            await self._synchronize_node(sync_level)
        else:
            sync_level = min(sync_level, subsquid_sync_level)
            await self._synchronize_subsquid(sync_level)

        if not self.node_datasources and not self._subsquid_started:
            self._subsquid_started = True
            self._logger.info('No `evm.node` datasources available; polling Subsquid')
            for datasource in self.subsquid_datasources:
                await datasource.start()

        await self._exit_sync_state(sync_level)
