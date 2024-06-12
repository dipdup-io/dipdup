import random
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Generic
from typing import TypeVar

from web3 import Web3

from dipdup.config import EvmIndexConfigU
from dipdup.config.evm import EvmContractConfig
from dipdup.datasources.evm_node import NODE_LAST_MILE
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.index import Index
from dipdup.index import IndexQueueItemT
from dipdup.models.subsquid import SubsquidMessageType
from dipdup.package import DipDupPackage
from dipdup.prometheus import Metrics

if TYPE_CHECKING:
    from dipdup.context import DipDupContext

EVM_SUBSQUID_READAHEAD_LIMIT = 10000

IndexConfigT = TypeVar('IndexConfigT', bound=EvmIndexConfigU)
DatasourceT = TypeVar('DatasourceT', bound=EvmSubsquidDatasource | EvmNodeDatasource)


_sighashes: dict[str, str] = {}


def get_sighash(package: DipDupPackage, method: str, to: EvmContractConfig | None = None) -> str:
    """Method in config is either a full signature or a method name. We need to convert it to a sighash first."""
    key = method + (to.module_name if to else '')
    if key in _sighashes:
        return _sighashes[key]

    if {'(', ')'} <= set(method) and not to:
        _sighashes[key] = Web3.keccak(text=method).hex()[:10]
    elif to:
        _sighashes[key] = package.get_converted_evm_abi(to.module_name)['methods'][method]['sighash']
    else:
        raise ConfigurationError('`to` field is missing; `method` is expected to be a full signature')
    return _sighashes[key]


class EvmIndex(
    Generic[IndexConfigT, IndexQueueItemT, DatasourceT],
    Index[IndexConfigT, IndexQueueItemT, DatasourceT],
    ABC,
    message_type=SubsquidMessageType,  # type: ignore[arg-type]
):
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
