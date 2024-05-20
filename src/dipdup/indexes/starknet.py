from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Generic
from typing import TypeVar
from typing import cast

from dipdup.config import StarknetIndexConfigU
from dipdup.datasources import IndexDatasource
from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import IndexQueueItemT
from dipdup.models.subsquid import SubsquidMessageType
from dipdup.prometheus import Metrics

IndexConfigT = TypeVar('IndexConfigT', bound=StarknetIndexConfigU)
DatasourceT = TypeVar('DatasourceT', bound=StarknetSubsquidDatasource)

if TYPE_CHECKING:
    from dipdup.context import DipDupContext

class StarknetIndex(
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
        self.subsquid_datasources = tuple(d for d in datasources if isinstance(d, StarknetSubsquidDatasource))
        self._subsquid_started: bool = False

    @abstractmethod
    async def _synchronize_subsquid(self, sync_level: int) -> None: ...

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        sync_levels = set()
        for sub in self._config.get_subscriptions():
            for datasource in self._datasources:
                if not isinstance(datasource, IndexDatasource):
                    continue
                sync_levels.add(datasource.get_sync_level(sub))

        if None in sync_levels:
            sync_levels.remove(None)
        if not sync_levels:
            raise FrameworkException('Initialize config before starting `IndexDispatcher`')

        # NOTE: Multiple sync levels means index with new subscriptions was added in runtime.
        # NOTE: Choose the highest level; outdated realtime messages will be dropped from the queue anyway.
        return max(cast(set[int], sync_levels))

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch event logs via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        levels_left = sync_level - index_level
        if levels_left <= 0:
            return

        if not self.subsquid_datasources:
            raise ConfigurationError('No subsquid datasources available.')

        subsquid_sync_level = await self.subsquid_datasources[0].get_head_level()
        Metrics.set_sqd_processor_chain_height(subsquid_sync_level)

        # NOTE: Handle other datasources below
        self._logger.info('Found subsquid datasource; using Subsquid')

        sync_level = min(sync_level, subsquid_sync_level)
        await self._synchronize_subsquid(sync_level)

        if not self._subsquid_started:
            self._subsquid_started = True
            self._logger.info('Starting Subsquid polling')
            for datasource in self.subsquid_datasources:
                await datasource.start()

        await self._exit_sync_state(sync_level)
