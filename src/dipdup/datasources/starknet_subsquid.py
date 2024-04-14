from dipdup.datasources.abstract_subsquid import AbstractSubsquidDatasource, AbstractSubsquidWorker


StarknetQuery = {}


class _StarknetSubsquidWorker(AbstractSubsquidWorker):
    async def query(self, query: StarknetQuery) -> list[dict[str, Any]]:  # TODO: fix typing
        return await super().query(query)

class StarknetSubsquidDatasource(AbstractSubsquidDatasource):

    def __init__(self, config: StarknetSubsquidDatasourceConfig) -> None:
        super().__init__(config, False)

    async def _get_worker(self, level: int) -> _StarknetSubsquidWorker:
        return StarknetSubsquidWorker(await self._fetch_worker(level))

    async def query_worker(self, query: StarknetQuery, current_level: int) -> list[dict[str, Any]]:  # TODO: fix typing
        return await super().query_worker(query, current_level)

    async def iter_event_logs(
        self,
        topics: tuple[tuple[str | None, str], ...],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[StarknetSubsquidEventData, ...]]:
        raise NotImplementedError()

    async def iter_transactions(
        self,
        first_level: int,
        last_level: int,
        filters: tuple[TransactionRequest, ...],
    ) -> AsyncIterator[tuple[StarknetSubsquidTransactionData, ...]]:
        raise NotImplementedError()
