import asyncio
import zipfile
from collections import defaultdict
from collections import deque
from io import BytesIO
from typing import Any
from typing import AsyncIterator

import pyarrow.ipc  # type: ignore[import]

from dipdup.config import HttpConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.models.evm_subsquid import LogFieldSelection
from dipdup.models.evm_subsquid import LogRequest
from dipdup.models.evm_subsquid import Query
from dipdup.models.evm_subsquid import SubsquidEventData

LOG_FIELDS: LogFieldSelection = {
    'logIndex': True,
    'transactionIndex': True,
    'transactionHash': True,
    'address': True,
    'data': True,
    'topics': True,
    # 'blockNumber': True,
    # 'blockHash': True,
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
            await asyncio.sleep(1)
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

        # TODO: smarter query optimizator
        topics_by_address = defaultdict(list)
        for address, topic in topics:
            topics_by_address[address].append(topic)

        log_request = [
            LogRequest(
                address=[a] if a else [],
                topic0=t,
            )
            for a, t in topics_by_address.items()
        ]

        while current_level <= last_level:
            worker_url = (
                await self._http.request(
                    'get',
                    f'{self._config.url}/{current_level}/worker',
                )
            ).decode()

            query: Query = {
                'logs': log_request,
                'fields': {
                    'block': {},
                    'log': LOG_FIELDS,
                },
                'fromBlock': current_level,
                'toBlock': last_level,
            }

            response: list[dict[str, Any]] = await self.request(
                'post',
                url=worker_url,
                json=query,
            )

            for level_logs in response:
                level = level_logs['header']['number']
                current_level = level + 1
                logs: deque[SubsquidEventData] = deque()
                for raw_log in level_logs['logs']:
                    logs.append(
                        SubsquidEventData.from_json(raw_log, level),
                    )
                yield tuple(logs)

    async def initialize(self) -> None:
        level = await self.get_head_level()

        if not level:
            raise DatasourceError('Archive is not ready yet', self.name)

        self.set_sync_level(None, level)

    async def get_head_level(self) -> int:
        response = await self.request('get', 'height')
        return int(response)
