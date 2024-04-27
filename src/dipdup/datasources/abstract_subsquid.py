
# TODO: implement and move models
import asyncio
from copy import copy
from typing import Any
from typing import cast

from dipdup.config import HttpConfig
from dipdup.datasources import Datasource
from dipdup.datasources import DatasourceConfigT
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.http import safe_exceptions

AbstractSubsquidQuery = dict[str, Any]

# class AbstractSubsquidQuery(TypedDict):
#     fromBlock: int
#     toBlock: NotRequired[int]
#     includeAllBlocks: NotRequired[bool]
#     fields: NotRequired[FieldSelection]

class AbstractSubsquidWorker(Datasource[Any]):
    async def run(self) -> None:
        raise FrameworkException('Subsquid worker datasource should not be run')

    async def query(self, query: AbstractSubsquidQuery) -> list[dict[str, Any]]:
        self._logger.debug('Worker query: %s', query)
        response = await self.request(
            'post',
            url='',
            json=query,
        )
        return cast(list[dict[str, Any]], response)


class AbstractSubsquidDatasource(IndexDatasource):
    _default_http_config = HttpConfig(
        polling_interval=1.0,
    )

    def __init__(self, config: Any) -> None:
        self._started = asyncio.Event()
        super().__init__(config, False)

    async def run(self) -> None:
        await self._started.wait()

        # NOTE: If node datasource is missing, just poll API in reasonable intervals.
        while True:
            await asyncio.sleep(self._http_config.polling_interval)
            await self.initialize()

    async def start(self) -> None:
        self._started.set()

    async def subscribe(self) -> None:
        pass

    # FIXME: Heavily copy-pasted from `HTTPGateway._retry_request`
    async def query_worker(self, query: AbstractSubsquidQuery, current_level: int) -> list[dict[str, Any]]:
        retry_sleep = self._http_config.retry_sleep
        attempt = 1
        last_attempt = self._http_config.retry_count + 1

        while True:
            try:
                # TODO: What is the logic here?
                # NOTE: Request a fresh worker after each failed attempt
                worker_datasource = await self._get_worker(current_level)
                async with worker_datasource:
                    return await worker_datasource.query(query)
            except safe_exceptions as e:
                self._logger.warning('Worker query attempt %s/%s failed: %s', attempt, last_attempt, e)
                if attempt == last_attempt:
                    raise e

                self._logger.info('Waiting %s seconds before retry', retry_sleep)
                await asyncio.sleep(retry_sleep)

                attempt += 1
                retry_sleep *= self._http_config.retry_multiplier

    async def initialize(self) -> None:
        level = await self.get_head_level()

        if not level:
            raise DatasourceError('Subsquid is not ready yet', self.name)

        self.set_sync_level(None, level)


    async def get_head_level(self) -> int:
        response = await self.request('get', 'height')
        return int(response)

    async def _fetch_worker(self, level: int) -> DatasourceConfigT:
        worker_url = (
            await self._http.request(
                'get',
                f'{self._config.url}/{level}/worker',
            )
        ).decode()

        worker_config: DatasourceConfigT = copy(self._config)
        worker_config.url = worker_url
        if not worker_config.http:
            worker_config.http = self._default_http_config

        # NOTE: Fail immediately; retries are handled one level up
        if worker_config.http:
            worker_config.http.retry_count = 0

        return worker_config

    async def _get_worker(self, level: int) -> AbstractSubsquidWorker:
        return AbstractSubsquidWorker(await self._fetch_worker(level))
    