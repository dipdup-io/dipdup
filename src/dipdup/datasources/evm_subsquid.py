import asyncio
import zipfile
from collections import defaultdict
from collections import deque
from collections.abc import AsyncIterator
from copy import copy
from io import BytesIO
from typing import Any

import pyarrow.ipc  # type: ignore[import-untyped]

from dipdup.config import HttpConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import Datasource
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.models.evm_subsquid import LogFieldSelection
from dipdup.models.evm_subsquid import LogRequest
from dipdup.models.evm_subsquid import Query
from dipdup.models.evm_subsquid import SubsquidEventData

POLL_INTERVAL = 1
LOG_FIELDS: LogFieldSelection = {
    'logIndex': True,
    'transactionIndex': True,
    'transactionHash': True,
    'address': True,
    'data': True,
    'topics': True,
}


def unpack_data(content: bytes) -> dict[str, list[dict[str, Any]]]:
    """Extract bytes from Subsquid zip+pyarrow archives"""
    data = {}
    with zipfile.ZipFile(BytesIO(content), 'r') as arch:
        for item in arch.filelist:  # The set of files depends on requested data
            with arch.open(item) as f, pyarrow.ipc.open_stream(f) as reader:
                table: pyarrow.Table = reader.read_all()
                data[item.filename] = table.to_pylist()
    return data


class SubsquidDatasource(IndexDatasource[SubsquidDatasourceConfig]):
    _default_http_config = HttpConfig()

    def __init__(self, config: SubsquidDatasourceConfig) -> None:
        super().__init__(config, False)

    async def run(self) -> None:
        if self._config.node:
            return
        # NOTE: If node datasource is missing, just poll archive in reasonable intervals
        # NOTE: Subsquid archives are expected to get real-time support in the future
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            await self.initialize()

    async def subscribe(self) -> None:
        pass

    async def iter_event_logs(
        self,
        topics: list[tuple[str | None, str]],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[SubsquidEventData, ...]]:
        current_level = first_level

        # TODO: Smarter query optimizator
        topics_by_address = defaultdict(list)
        for address, topic in topics:
            topics_by_address[address].append(topic)

        log_request: list[LogRequest] = []
        for address, topic_list in topics_by_address.items():
            if address:
                log_request.append(LogRequest(address=[address], topic0=topic_list))
            else:
                log_request.append(LogRequest(topic0=topic_list))

        while current_level <= last_level:
            worker_url = (
                await self._http.request(
                    'get',
                    f'{self._config.url}/{current_level}/worker',
                )
            ).decode()
            worker_config = copy(self._config)
            worker_config.url = worker_url
            worker_datasource: _SubsquidWorker = _SubsquidWorker(worker_config)

            query: Query = {
                'logs': log_request,
                'fields': {
                    'block': {
                        'timestamp': True,
                    },
                    'log': LOG_FIELDS,
                },
                'fromBlock': current_level,
                'toBlock': last_level,
            }
            self._logger.debug('Worker query: %s', query)

            async with worker_datasource:
                response: list[dict[str, Any]] = await worker_datasource.request(
                    'post',
                    url=worker_url,
                    json=query,
                )

            for level_logs in response:
                level = level_logs['header']['number']
                timestamp = level_logs['header']['timestamp']
                current_level = level + 1
                logs: deque[SubsquidEventData] = deque()
                for raw_log in level_logs['logs']:
                    logs.append(
                        SubsquidEventData.from_json(raw_log, level, timestamp),
                    )
                yield tuple(logs)

    async def initialize(self) -> None:
        level = await self.get_head_level()

        if not level:
            raise DatasourceError('Subsquid is not ready yet', self.name)

        self.set_sync_level(None, level)

    async def get_head_level(self) -> int:
        response = await self.request('get', 'height')
        return int(response)


class _SubsquidWorker(Datasource[Any]):
    async def run(self) -> None:
        pass
