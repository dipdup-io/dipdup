from dataclasses import dataclass
from typing import Any
from typing import cast

from marshmallow import EXCLUDE
from starknet_py.net.client_models import BlockStatus
from starknet_py.net.client_models import EmittedEvent
from starknet_py.net.client_models import Hash
from starknet_py.net.client_models import L1DAMode
from starknet_py.net.client_models import PendingStarknetBlock
from starknet_py.net.client_models import ResourcePrice
from starknet_py.net.client_models import Tag
from starknet_py.net.client_models import Transaction
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.full_node_client import get_block_identifier

from dipdup.config import HttpConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.datasources.evm_node import EvmNodeDatasource


@dataclass(kw_only=True)
class BlockHeader:
    """
    Dataclass representing a block header.
    """

    # pylint: disable=too-many-instance-attributes

    block_hash: int
    parent_hash: int
    block_number: int
    new_root: int
    timestamp: int
    sequencer_address: int
    l1_gas_price: ResourcePrice
    starknet_version: str
    l1_data_gas_price: ResourcePrice | None = None
    l1_da_mode: L1DAMode | None = None


@dataclass
class StarknetBlock(BlockHeader):
    """
    Dataclass representing a block on Starknet.
    """

    status: BlockStatus
    transactions: list[Transaction]


class StarknetClient(FullNodeClient):
    async def get_block(
        self,
        block_hash: Hash | Tag | None = None,
        block_number: int | Tag | None = None,
    ) -> StarknetBlock | PendingStarknetBlock:
        block_identifier = get_block_identifier(block_hash=block_hash, block_number=block_number)

        res = await self._client.call(
            method_name='getBlockWithTxs',
            params=block_identifier,
        )
        if block_identifier == {'block_id': 'pending'}:
            return PendingStarknetBlock(**res)
        return StarknetBlock(**res)


class StarknetNodeDatasource(EvmNodeDatasource):

    def __init__(self, config: EvmNodeDatasourceConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(config, merge_subscriptions)
        self._client = StarknetClient(config.url)

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
