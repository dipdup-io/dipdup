from contextlib import ExitStack

from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesHandlerConfig
from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesIndexConfig
from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.indexes.tezos_tzkt_token_balances.fetcher import TokenBalanceFetcher
from dipdup.indexes.tezos_tzkt_token_balances.matcher import match_token_balances
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktRollbackMessage
from dipdup.models.tezos_tzkt import TzktTokenBalanceData
from dipdup.prometheus import Metrics

TokenBalanceQueueItem = tuple[TzktTokenBalanceData, ...] | TzktRollbackMessage


class TzktTokenBalancesIndex(
    Index[TzktTokenBalancesIndexConfig, TokenBalanceQueueItem, TzktDatasource],
    message_type=TzktMessageType.token_balance,
):
    def push_token_balances(self, token_balances: TokenBalanceQueueItem) -> None:
        self.push_realtime_message(token_balances)

    def _create_fetcher(self, first_level: int, last_level: int) -> TokenBalanceFetcher:
        token_addresses: set[str] = set()
        token_ids: set[int] = set()
        for handler_config in self._config.handlers:
            if handler_config.contract:
                token_addresses.add(handler_config.contract.get_address())
            if handler_config.token_id is not None:
                token_ids.add(handler_config.token_id)

        return TokenBalanceFetcher(
            datasource=self._datasource,
            token_addresses=token_addresses,
            token_ids=token_ids,
            first_level=first_level,
            last_level=last_level,
        )

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch token balances via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        first_level = index_level + 1
        self._logger.info('Fetching token balances from level %s to %s', first_level, sync_level)
        fetcher = self._create_fetcher(first_level, sync_level)

        async for level, token_balances in fetcher.fetch_by_level():
            with ExitStack() as stack:
                if Metrics.enabled:
                    Metrics.set_levels_to_sync(self._config.name, sync_level - level)
                    stack.enter_context(Metrics.measure_level_sync_duration())
                await self._process_level_token_balances(token_balances, sync_level)

        await self._exit_sync_state(sync_level)

    async def _process_level_token_balances(
        self,
        token_balances: tuple[TzktTokenBalanceData, ...],
        sync_level: int,
    ) -> None:
        if not token_balances:
            return

        batch_level = token_balances[0].level
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing token balances of level %s', batch_level)
        matched_handlers = match_token_balances(self._config.handlers, token_balances)

        if Metrics.enabled:
            Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self._update_state(level=batch_level)
            return

        async with self._ctx.transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, token_balance in matched_handlers:
                await self._call_matched_handler(handler_config, token_balance)
            await self._update_state(level=batch_level)

    async def _call_matched_handler(
        self, handler_config: TzktTokenBalancesHandlerConfig, token_balance: TzktTokenBalanceData
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            # NOTE: missing `operation_id` field in API to identify operation
            None,
            token_balance,
        )

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

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_level_realtime_duration())
                await self._process_level_token_balances(message, message_level)
