import asyncio
from typing import TYPE_CHECKING

from dipdup.config import HttpConfig
from dipdup.config.starknet_node import StarknetNodeDatasourceConfig
from dipdup.datasources import IndexDatasource

if TYPE_CHECKING:
    from starknet_py.net.client_models import EventsChunk  # type: ignore[import-untyped]

    from dipdup.datasources._starknetpy import FullNodeClient


class StarknetNodeDatasource(IndexDatasource[StarknetNodeDatasourceConfig]):
    _default_http_config = HttpConfig(
        batch_size=1000,
    )

    def __init__(self, config: StarknetNodeDatasourceConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(config, merge_subscriptions)
        self._client: FullNodeClient | None = None

    @property
    def client(self) -> 'FullNodeClient':
        from dipdup.datasources._starknetpy import FullNodeClient

        if self._client is None:
            self._client = FullNodeClient(self)
        return self._client

    async def initialize(self) -> None:
        level = await self.get_head_level()
        self.set_sync_level(None, level)

    async def run(self) -> None:
        if self.realtime:
            raise NotImplementedError

        while True:
            level = await self.get_head_level()
            self.set_sync_level(None, level)
            await asyncio.sleep(self._http_config.polling_interval)

    @property
    def realtime(self) -> bool:
        return self._config.ws_url is not None

    async def subscribe(self) -> None:
        if not self.realtime:
            return

        raise NotImplementedError

    async def get_head_level(self) -> int:
        return await self.client.get_block_number()  # type: ignore[no-any-return]

    async def get_events(
        self,
        address: str | None,
        keys: list[list[str]] | None,
        first_level: int,
        last_level: int,
        continuation_token: str | None = None,
    ) -> 'EventsChunk':
        return await self.client.get_events(
            address=address,
            keys=keys,
            from_block_number=first_level,
            to_block_number=last_level,
            chunk_size=self._http_config.batch_size,
            continuation_token=continuation_token,
        )
