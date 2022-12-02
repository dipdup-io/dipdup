import logging
from abc import ABC
from abc import abstractmethod
from collections import deque
from contextlib import ExitStack
from typing import Any
from typing import Generic
from typing import Optional
from typing import Set
from typing import TypeVar
from typing import Union
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
from dipdup.models import BigMapData
from dipdup.models import EventData
from dipdup.models import OperationData
from dipdup.models import Origination
from dipdup.models import TokenTransferData
from dipdup.models import Transaction
from dipdup.prometheus import Metrics
from dipdup.utils import FormattedLogger

_logger = logging.getLogger(__name__)

IndexConfigT = TypeVar('IndexConfigT', bound=ResolvedIndexConfigU)
IndexQueueItemT = TypeVar('IndexQueueItemT', bound=Any)
IndexDatasourceT = TypeVar('IndexDatasourceT', bound=IndexDatasource)

OperationHandlerArgumentT = Optional[Union[Transaction, Origination, OperationData]]


# TODO: Not used in some indexes
def extract_level(
    message: tuple[OperationData | BigMapData | TokenTransferData | EventData, ...],
) -> int:
    """Safely extract level from raw messages batch"""
    # TODO: Skip conditionally
    batch_levels = {(i.level, i.__class__) for i in message}
    if len(batch_levels) != 1:
        raise FrameworkException(f'Items in data batch have different levels: {batch_levels}')
    return batch_levels.pop()[0]


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
        self._state: Optional[models.Index] = None

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
        return max(cast(Set[int], sync_levels))

    async def initialize_state(self, state: Optional[models.Index] = None) -> None:
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
        if self.name in rolled_back_indexes:
            await self.state.refresh_from_db(('level',))
            rolled_back_indexes.remove(self.name)

        if not isinstance(self._config, HeadIndexConfig) and self._config.last_level:
            head_level = self._config.last_level
            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_total_sync_duration())
                await self._synchronize(head_level)
            await self.state.update_status(IndexStatus.ONESHOT, head_level)

        index_level = self.state.level
        sync_level = self.get_sync_level()

        if index_level < sync_level:
            self._logger.info('Index is behind the datasource level, syncing: %s -> %s', index_level, sync_level)
            self._queue.clear()

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_total_sync_duration())
                await self._synchronize(sync_level)

        elif self._queue:
            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_total_realtime_duration())
                await self._process_queue()
        else:
            return False
        return True

    async def _enter_sync_state(self, head_level: int) -> Optional[int]:
        # NOTE: Final state for indexes with `last_level`
        if self.state.status == IndexStatus.ONESHOT:
            return None

        index_level = self.state.level

        if index_level == head_level:
            return None
        if index_level > head_level:
            raise FrameworkException(f'Attempt to synchronize index from level {index_level} to level {head_level}')

        self._logger.info('Synchronizing index to level %s', head_level)
        await self.state.update_status(status=IndexStatus.SYNCING, level=index_level)
        return index_level

    async def _exit_sync_state(self, head_level: int) -> None:
        self._logger.info('Index is synchronized to level %s', head_level)
        if Metrics.enabled:
            Metrics.set_levels_to_sync(self._config.name, 0)
        await self.state.update_status(status=IndexStatus.REALTIME, level=head_level)
