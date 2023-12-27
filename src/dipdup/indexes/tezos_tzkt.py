from abc import abstractmethod
from collections import deque
from typing import Any
from typing import Generic

from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import IndexConfigT
from dipdup.index import IndexQueueItemT
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktRollbackMessage
from dipdup.prometheus import Metrics


class TzktIndex(
    Generic[IndexConfigT, IndexQueueItemT],
    Index[Any, Any, TzktDatasource],
    message_type=TzktMessageType,
):
    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        if self._queue:
            self._logger.debug('Processing websocket queue')
        while self._queue:
            message = self._queue.popleft()
            if isinstance(message, TzktRollbackMessage):
                await self._tzkt_rollback(message.from_level, message.to_level)
                continue

            message_level = message[0].level
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            await self._process_level_data(message, message_level)

    async def _process_level_data(
        self,
        level_data: IndexQueueItemT,
        sync_level: int,
    ) -> None:
        if not level_data:
            return

        batch_level = level_data[0].level
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing data of level %s', batch_level)
        matched_handlers = self._match_level_data(self._config.handlers, level_data)

        Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self._update_state(level=batch_level)
            return

        async with self._ctx.transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, data in matched_handlers:
                await self._call_matched_handler(handler_config, data)
            await self._update_state(level=batch_level)

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
