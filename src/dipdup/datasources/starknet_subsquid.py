from typing import Any, AsyncIterator

from dipdup.datasources.abstract_subsquid import AbstractSubsquidDatasource
from dipdup.datasources.abstract_subsquid import AbstractSubsquidWorker

# ----------------

# from dipdup.models.starknet_subsquid import Query
# from dipdup.config.starknet_subsquid import StarknetSubsquidDatasourceConfig
# from dipdup.models.starknet import StarknetTransactionData
# from dipdup.models.starknet import StarknetEventData
# from dipdup.models.starknet_subsquid import TransactionRequest

from dipdup.config import DatasourceConfig

Query = dict
StarknetSubsquidDatasourceConfig = DatasourceConfig
StarknetTransactionData = dict
StarknetEventData = dict
TransactionRequest = dict


class _StarknetSubsquidWorker(AbstractSubsquidWorker):
    async def query(self, query: Query) -> list[dict[str, Any]]:  # TODO: fix typing
        return await super().query(query)

class StarknetSubsquidDatasource(AbstractSubsquidDatasource):

    def __init__(self, config: StarknetSubsquidDatasourceConfig) -> None:
        super().__init__(config, False)

    async def _get_worker(self, level: int) -> _StarknetSubsquidWorker:
        return _StarknetSubsquidWorker(await self._fetch_worker(level))

    async def query_worker(self, query: Query, current_level: int) -> list[dict[str, Any]]:  # TODO: fix typing
        return await super().query_worker(query, current_level)

    async def iter_event_logs(
        self,
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[StarknetEventData, ...]]:
        raise NotImplementedError()

    async def iter_transactions(
        self,
        first_level: int,
        last_level: int,
        filters: tuple[TransactionRequest, ...],
    ) -> AsyncIterator[tuple[StarknetTransactionData, ...]]:
        raise NotImplementedError()
