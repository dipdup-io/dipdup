from abc import ABC
from abc import abstractmethod
from collections import deque
from contextlib import ExitStack
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import cast

import dipdup.models as models
from dipdup.config import HeadIndexConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.context import DipDupContext
from dipdup.context import rolled_back_indexes
from dipdup.datasources.datasource import IndexDatasource
from dipdup.enums import IndexStatus
from dipdup.enums import MessageType
from dipdup.exceptions import FrameworkException
from dipdup.prometheus import Metrics
from dipdup.utils import FormattedLogger

IndexConfigT = TypeVar('IndexConfigT', bound=ResolvedIndexConfigU)
IndexQueueItemT = TypeVar('IndexQueueItemT', bound=Any)
IndexDatasourceT = TypeVar('IndexDatasourceT', bound=IndexDatasource)


class Index(ABC, Generic[IndexConfigT, IndexQueueItemT, IndexDatasourceT]):
    """Base class for index implementations

    Provides common interface for managing index state and switching between sync and realtime modes.
    """

    message_type: MessageType

    def __init_subclass__(cls, message_type: MessageType) -> None:
        cls.message_type = message_type
        return super().__init_subclass__()

    def __init__(
        self,
        ctx: DipDupContext,
        config: IndexConfigT,
        datasource: IndexDatasourceT,
    ) -> None:
        self._ctx = ctx
        self._config = config
        self._datasource = datasource
        self._queue: deque[IndexQueueItemT] = deque()

        self._logger = FormattedLogger('dipdup.index', fmt=f'{config.name}: ' + '{}')
        self._state: models.Index | None = None

    def push_realtime_message(self, message: IndexQueueItemT) -> None:
        """Push message to the queue"""
        self._queue.append(message)

        if Metrics.enabled:
            Metrics.set_levels_to_realtime(self._config.name, len(self._queue))

    @abstractmethod
    async def _synchronize(self, sync_level: int) -> None:
        """Process historical data before switching to realtime mode"""
        ...

    @abstractmethod
    async def _process_queue(self) -> None:
        """Process realtime queue"""
        ...

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def datasource(self) -> IndexDatasourceT:
        return self._datasource

    @property
    def state(self) -> models.Index:
        if self._state is None:
            raise FrameworkException('Index state is not initialized')
        return self._state

    @property
    def synchronized(self) -> bool:
        return self.state.status == IndexStatus.REALTIME

    @property
    def realtime(self) -> bool:
        return self.state.status == IndexStatus.REALTIME and not self._queue

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        sync_levels = {self.datasource.get_sync_level(s) for s in self._config.subscriptions}
        if not sync_levels:
            raise FrameworkException('Initialize config before starting `IndexDispatcher`')
        if None in sync_levels:
            raise FrameworkException('Call `set_sync_level` before starting `IndexDispatcher`')
        # NOTE: Multiple sync levels means index with new subscriptions was added in runtime.
        # NOTE: Choose the highest level; outdated realtime messages will be dropped from the queue anyway.
        return max(cast(set[int], sync_levels))

    async def initialize_state(self, state: models.Index | None = None) -> None:
        if self._state:
            raise FrameworkException('Index state is already initialized')

        if state:
            self._state = state
            return

        index_level = 0
        if not isinstance(self._config, HeadIndexConfig) and self._config.first_level:
            # NOTE: Be careful there: index has not reached the first level yet
            index_level = self._config.first_level - 1

        self._state, _ = await models.Index.get_or_create(
            name=self._config.name,
            type=self._config.kind,
            defaults={
                'level': index_level,
                'config_hash': self._config.hash(),
                'template': self._config.parent.name if self._config.parent else None,
                'template_values': self._config.template_values,
            },
        )

    async def process(self) -> bool:
        if self.state.status == IndexStatus.ONESHOT:
            raise FrameworkException('Index is in oneshot state and cannot be processed')

        if self.name in rolled_back_indexes:
            await self.state.refresh_from_db(('level',))
            rolled_back_indexes.remove(self.name)

        last_level = self._config.last_level
        if last_level and not isinstance(self._config, HeadIndexConfig):
            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_total_sync_duration())
                await self._synchronize(last_level)
                await self._enter_disabled_state(last_level)
                return True

        index_level = self.state.level
        sync_level = self.get_sync_level()

        if index_level < sync_level:
            self._logger.info('Index is behind the datasource level, syncing: %s -> %s', index_level, sync_level)
            self._queue.clear()

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_total_sync_duration())
                await self._synchronize(sync_level)
                return True

        if self._queue:
            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_total_realtime_duration())
                await self._process_queue()
                return True

        return False

    async def _enter_sync_state(self, head_level: int) -> int | None:
        index_level = self.state.level

        if index_level == head_level:
            return None
        if index_level > head_level:
            raise FrameworkException(f'Attempt to synchronize index from level {index_level} to level {head_level}')

        self._logger.info('Synchronizing index to level %s', head_level)
        await self._update_state(status=IndexStatus.SYNCING, level=index_level)
        return index_level

    async def _exit_sync_state(self, head_level: int) -> None:
        self._logger.info('Index is synchronized to level %s', head_level)
        if Metrics.enabled:
            Metrics.set_levels_to_sync(self._config.name, 0)
        await self._update_state(status=IndexStatus.REALTIME, level=head_level)

    async def _enter_disabled_state(self, last_level: int) -> None:
        self._logger.info('Index is synchronized to level %s', last_level)
        if Metrics.enabled:
            Metrics.set_levels_to_sync(self._config.name, 0)
        await self._update_state(status=IndexStatus.ONESHOT, level=last_level)

    async def _update_state(
        self,
        status: IndexStatus | None = None,
        level: int | None = None,
    ) -> None:
        state = self.state
        state.status = status or state.status
        state.level = level or state.level
        await state.save()

    # TODO: Move to TezosTzktIndex
    async def _tzkt_rollback(
        self,
        from_level: int,
        to_level: int,
    ) -> None:
        hook_name = 'on_index_rollback'
        self._logger.warning('Affected by rollback; firing `%s` hook', self.name, hook_name)
        await self._ctx.fire_hook(
            name=hook_name,
            index=self,
            from_level=from_level,
            to_level=to_level,
        )
