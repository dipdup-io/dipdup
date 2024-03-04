import time
from abc import ABC
from abc import abstractmethod
from collections import deque
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import cast

import dipdup.models as models
from dipdup.config import ResolvedIndexConfigU
from dipdup.context import DipDupContext
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import FrameworkException
from dipdup.models import IndexStatus
from dipdup.models import MessageType
from dipdup.models import RollbackMessage
from dipdup.performance import metrics
from dipdup.performance import queues
from dipdup.prometheus import Metrics
from dipdup.utils import FormattedLogger

IndexConfigT = TypeVar('IndexConfigT', bound=ResolvedIndexConfigU)
IndexQueueItemT = TypeVar('IndexQueueItemT', bound=Any)
IndexDatasourceT = TypeVar('IndexDatasourceT', bound=IndexDatasource[Any])


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
        queues.add_queue(self._queue, f'index_realtime:{config.name}:{id(self)})')

        self._logger = FormattedLogger(__name__, fmt=f'{config.name}: ' + '{}')
        self._state: models.Index | None = None

    @property
    def datasources(self) -> tuple[IndexDatasource[Any], ...]:
        return (self.datasource,)

    def push_realtime_message(self, message: IndexQueueItemT) -> None:
        """Push message to the queue"""
        self._queue.append(message)

        Metrics.set_levels_to_realtime(self._config.name, len(self._queue))

    @abstractmethod
    async def _synchronize(self, sync_level: int) -> None:
        """Process historical data before switching to realtime mode"""
        ...

    @abstractmethod
    def _match_level_data(
        self,
        handlers: Any,
        level_data: Any,
    ) -> deque[Any]: ...

    @abstractmethod
    async def _call_matched_handler(
        self,
        handler_config: Any,
        level_data: Any,
    ) -> None: ...

    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        if self._queue:
            self._logger.debug('Processing websocket queue')
        while self._queue:
            message = self._queue.popleft()
            if not message:
                raise FrameworkException('Empty message in the queue')

            if isinstance(message, RollbackMessage):
                await self._rollback(message.from_level, message.to_level)
                continue

            message_level = message[0].level
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            await self._process_level_data(message, message_level)

    async def _process_level_data(
        self,
        level_data: Any,
        sync_level: int,
    ) -> None:
        if not level_data:
            return

        batch_level = level_data[0].level
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing data of level %s', batch_level)
        started_at = time.time()

        # FIXME: TzktHeadIndexConfig, TzktOperationsUnfilteredIndexConfig still use own methods; see FIXMEs
        matched_handlers = self._match_level_data(self._config.handlers, level_data)  # type: ignore[union-attr]

        total_matched = len(matched_handlers)
        Metrics.set_index_handlers_matched(total_matched)
        metrics[f'{self.name}:handlers_matched'] += total_matched
        metrics[f'{self.name}:time_in_matcher'] += (time.time() - started_at) / 60

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self._update_state(level=batch_level)
            return

        started_at = time.time()
        async with self._ctx.transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, data in matched_handlers:
                await self._call_matched_handler(handler_config, data)
            await self._update_state(level=batch_level)
        metrics[f'{self.name}:time_in_callbacks'] += (time.time() - started_at) / 60

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
        return self.state.status == IndexStatus.realtime

    @property
    def realtime(self) -> bool:
        return self.state.status == IndexStatus.realtime and not self._queue

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        subs = self._config.get_subscriptions()
        sync_levels = {self.datasource.get_sync_level(s) for s in subs}
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
        if self._config.first_level:
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
        if self.state.status == IndexStatus.disabled:
            raise FrameworkException('Index is in oneshot state and cannot be processed')

        if self.name in self._ctx._rolled_back_indexes:
            await self.state.refresh_from_db(('level',))
            self._ctx._rolled_back_indexes.remove(self.name)

        last_level = self._config.last_level
        if last_level:
            with Metrics.measure_total_sync_duration():
                await self._synchronize(last_level)
                await self._enter_disabled_state(last_level)
                return True

        index_level = self.state.level
        sync_level = self.get_sync_level()

        if index_level < sync_level:
            self._logger.info('Index is behind the datasource level, syncing: %s -> %s', index_level, sync_level)
            self._queue.clear()

            with Metrics.measure_total_sync_duration():
                await self._synchronize(sync_level)
                return True

        if self._queue:
            with Metrics.measure_total_realtime_duration():
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
        await self._update_state(status=IndexStatus.syncing, level=index_level)
        return index_level

    async def _exit_sync_state(self, head_level: int) -> None:
        self._logger.info('Index is synchronized to level %s', head_level)
        Metrics.set_levels_to_sync(self._config.name, 0)
        await self._update_state(status=IndexStatus.realtime, level=head_level)

    async def _enter_disabled_state(self, last_level: int) -> None:
        self._logger.info('Index is synchronized to level %s', last_level)
        Metrics.set_levels_to_sync(self._config.name, 0)
        await self._update_state(status=IndexStatus.disabled, level=last_level)

    async def _update_state(
        self,
        status: IndexStatus | None = None,
        level: int | None = None,
    ) -> None:
        state = self.state
        if level:
            self._logger.debug('Level updated: %s -> %s', state.level, level)
        if status:
            self._logger.info('Status updated: %s -> %s', state.status, status)
        state.status = status or state.status
        state.level = level or state.level
        await state.save()

    async def _rollback(
        self,
        from_level: int,
        to_level: int,
    ) -> None:
        hook_name = 'on_index_rollback'
        await self._ctx.fire_hook(
            name=hook_name,
            index=self,
            from_level=from_level,
            to_level=to_level,
        )
        await self._update_state(level=to_level)
