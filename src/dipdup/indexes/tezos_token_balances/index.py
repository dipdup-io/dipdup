from collections import deque
from typing import Any

from dipdup.config.tezos_token_balances import TezosTokenBalancesIndexConfig
from dipdup.indexes.tezos_token_balances.matcher import match_token_balances
from dipdup.indexes.tezos_tzkt import TezosIndex
from dipdup.models import RollbackMessage
from dipdup.models.tezos import TezosTokenBalanceData
from dipdup.models.tezos_tzkt import TezosTzktMessageType

QueueItem = tuple[TezosTokenBalanceData, ...] | RollbackMessage


class TezosTokenBalancesIndex(
    TezosIndex[TezosTokenBalancesIndexConfig, QueueItem],
    message_type=TezosTzktMessageType.token_balance,
):
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
            async for balances_batch in self.random_datasource.iter_token_balances(
                addresses, token_ids, last_level=head_level
            ):
                matched_handlers = match_token_balances(self._config.handlers, balances_batch)
                for handler_config, matched_balance_data in matched_handlers:
                    await self._ctx.fire_handler(
                        name=handler_config.callback,
                        index=handler_config.parent.name,
                        args=(matched_balance_data,),
                    )

            await self._update_state(level=head_level)

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        return match_token_balances(handlers, level_data)
