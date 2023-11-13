from collections import deque
from typing import Any

from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesHandlerConfig
from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesIndexConfig
from dipdup.exceptions import ConfigInitializationException
from dipdup.indexes.tezos_tzkt import TzktIndex
from dipdup.indexes.tezos_tzkt_token_balances.matcher import match_token_balances
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktRollbackMessage
from dipdup.models.tezos_tzkt import TzktTokenBalanceData

TokenBalanceQueueItem = tuple[TzktTokenBalanceData, ...] | TzktRollbackMessage


class TzktTokenBalancesIndex(
    TzktIndex[TzktTokenBalancesIndexConfig, TokenBalanceQueueItem],
    message_type=TzktMessageType.token_balance,
):
    def push_token_balances(self, token_balances: TokenBalanceQueueItem) -> None:
        self.push_realtime_message(token_balances)

    async def _synchronize(self, sync_level: int) -> None:
        await self._enter_sync_state(sync_level)
        await self._synchronize_actual(sync_level)
        await self._exit_sync_state(sync_level)

    async def _synchronize_actual(self, head_level: int) -> None:
        """Retrieve data for the current level"""
        # TODO: think about logging and metrics

        addresses, token_ids = set(), set()
        for handler in self._config.handlers:
            if handler.contract and handler.contract.address is not None:
                addresses.add(handler.contract.address)
            if handler.token_id is not None:
                token_ids.add(handler.token_id)

        async with self._ctx.transactions.in_transaction(head_level, head_level, self.name):
            # NOTE: If index is out of date fetch balances as of the current head.
            async for balances_batch in self._datasource.iter_token_balances(
                addresses, token_ids, last_level=head_level
            ):
                matched_handlers = match_token_balances(self._config.handlers, balances_batch)
                for handler_config, matched_balance_data in matched_handlers:
                    await self._call_matched_handler(handler_config, matched_balance_data)

            await self._update_state(level=head_level)

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

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        return match_token_balances(handlers, level_data)
