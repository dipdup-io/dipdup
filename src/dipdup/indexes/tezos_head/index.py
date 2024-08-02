from collections import deque
from typing import Any

from dipdup.config.tezos_head import TezosHeadIndexConfig
from dipdup.exceptions import FrameworkException
from dipdup.indexes.tezos_tzkt import TezosIndex
from dipdup.models import IndexStatus
from dipdup.models import RollbackMessage
from dipdup.models.tezos import TezosHeadBlockData
from dipdup.models.tezos_tzkt import TezosTzktMessageType

HeadQueueItem = TezosHeadBlockData | RollbackMessage


class TezosHeadIndex(
    TezosIndex[TezosHeadIndexConfig, HeadQueueItem],
    message_type=TezosTzktMessageType.head,
):
    async def _synchronize(self, sync_level: int) -> None:
        self._logger.info('Setting index level to %s and moving on', sync_level)
        await self._update_state(status=IndexStatus.realtime, level=sync_level)

    # FIXME: Use method from Index
    async def _process_queue(self) -> None:
        while self._queue:
            message = self._queue.popleft()
            if isinstance(message, RollbackMessage):
                await self._rollback(message.from_level, message.to_level)
                continue

            message_level = message.level
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            self._logger.debug('Processing head realtime message, %s left in queue', len(self._queue))

            batch_level = message.level
            index_level = self.state.level
            if batch_level <= index_level:
                raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

            async with self._ctx.transactions.in_transaction(batch_level, message_level, self.name):
                self._logger.debug('Processing head info of level %s', batch_level)
                await self._ctx.fire_handler(
                    name=self._config.callback,
                    index=self._config.name,
                    args=(message,),
                )
                await self._update_state(level=batch_level)

    # FIXME: Use method from Index
    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        raise NotImplementedError
