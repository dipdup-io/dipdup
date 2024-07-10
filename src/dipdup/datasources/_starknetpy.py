from dataclasses import dataclass
from typing import Any

from starknet_py.net.client_models import BlockStatus  # type: ignore[import-untyped]
from starknet_py.net.client_models import Hash
from starknet_py.net.client_models import L1DAMode
from starknet_py.net.client_models import PendingStarknetBlock
from starknet_py.net.client_models import ResourcePrice
from starknet_py.net.client_models import Tag
from starknet_py.net.client_models import Transaction
from starknet_py.net.full_node_client import FullNodeClient as OriginalFullNodeClient  # type: ignore[import-untyped]
from starknet_py.net.full_node_client import get_block_identifier
from starknet_py.net.http_client import HttpMethod  # type: ignore[import-untyped]
from starknet_py.net.http_client import RpcHttpClient as OriginalRpcHttpClient

from dipdup.datasources import Datasource


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


class RpcHttpClient(OriginalRpcHttpClient):
    def __init__(self, datasource: Datasource):
        super().__init__(datasource.url)
        self._datasource = datasource

    async def request(
        self,
        address: str,
        http_method: HttpMethod,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    ):
        return await self._datasource.request(
            method=http_method.value,
            url='',
            params=params or {},
            json=payload or {},
        )


class FullNodeClient(OriginalFullNodeClient):
    def __init__(
        self,
        datasource: Datasource,
    ):
        self.url = datasource.url
        self._client = RpcHttpClient(datasource)

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
