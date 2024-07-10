from typing import Any

from starknet_py.net.client_models import EmittedEvent

from dipdup.config.starknet_node import StarknetNodeDatasourceConfig
from dipdup.datasources._starknetpy import FullNodeClient
from dipdup.datasources.evm_node import EvmNodeDatasource


class StarknetNodeDatasource(EvmNodeDatasource):

    def __init__(self, config: StarknetNodeDatasourceConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(config, merge_subscriptions)
        self._client = FullNodeClient(self)

    async def get_head_level(self) -> int:
        return await self._client.get_block_number()

    async def get_block_by_level(self, block_number: int, full_transactions: bool = False) -> dict[str, Any]:
        if full_transactions:
            return await self._client.get_block_with_txs(block_number=block_number)
        return await self._client.get_block(block_number=block_number)

    async def get_events(
        self,
        address: str | None,
        keys: list[list[str]] | None,
        first_level: int,
        last_level: int,
    ) -> list[EmittedEvent]:
        return await self._client.get_events(
            address=address,
            keys=keys,
            from_block_number=first_level,
            to_block_number=last_level,
            chunk_size=self._http_config.batch_size,
            follow_continuation_token=True,
        )
