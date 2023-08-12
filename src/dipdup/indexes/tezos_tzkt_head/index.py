from dipdup.config.tezos_tzkt_head import HeadHandlerConfig
from dipdup.config.tezos_tzkt_head import TzktHeadIndexConfig
from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.models import IndexStatus
from dipdup.models.tezos_tzkt import TzktHeadBlockData
from dipdup.models.tezos_tzkt import TzktMessageType

HeadQueueItem = TzktHeadBlockData


class TzktHeadIndex(
    Index[TzktHeadIndexConfig, HeadQueueItem, TzktDatasource],
    message_type=TzktMessageType.head,
):
    def push_head(self, events: HeadQueueItem) -> None:
        self.push_realtime_message(events)

    async def _synchronize(self, sync_level: int) -> None:
        self._logger.info('Setting index level to %s and moving on', sync_level)
        await self._update_state(status=IndexStatus.realtime, level=sync_level)

    async def _process_queue(self) -> None:
        while self._queue:
            head = self._queue.popleft()
            message_level = head.level
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            self._logger.debug('Processing head realtime message, %s left in queue', len(self._queue))

            batch_level = head.level
            index_level = self.state.level
            if batch_level <= index_level:
                raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

            async with self._ctx.transactions.in_transaction(batch_level, message_level, self.name):
                self._logger.debug('Processing head info of level %s', batch_level)
                await self._call_matched_handler(self._config.handler_config, head)
                await self._update_state(level=batch_level)

    async def _call_matched_handler(self, handler_config: HeadHandlerConfig, head: TzktHeadBlockData) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            head.hash,
            head,
        )
