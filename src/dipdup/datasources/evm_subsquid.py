import asyncio
import zipfile
from collections import defaultdict
from collections import deque
from io import BytesIO
from typing import Any
from typing import AsyncIterator
from typing import cast

import pyarrow.ipc  # type: ignore[import]

from dipdup.config import HttpConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.models.evm_subsquid import FieldSelection
from dipdup.models.evm_subsquid import Query
from dipdup.models.evm_subsquid import SubsquidEventData

LOG_FIELDS: FieldSelection = {  # type: ignore
    'address': True,
    'blockNumber': True,
    'data': True,
    'topics': True,
    'blockHash': True,
    'index': True,
    'transactionHash': True,
    'transactionIndex': True,
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

        while current_level <= last_level:
            query: Query = {  # type: ignore
                # 'logs': [make_log_filter(address, topics) for address, topics in topics_by_address.items()],
                'fromBlock': current_level,
                'toBlock': last_level,
            }

            response: dict[str, Any] = await self.request(
                'post',
                url='query',
                json=query,
            )

            # NOTE: There's also 'archiveHeight' field, but sync level updated in the main loop
            current_level = response['nextBlock']

            for level in response['data']:
                logs: deque[SubsquidEventData] = deque()
                for transaction in level:
                    for raw_log in transaction['logs']:
                        logs.append(
                            SubsquidEventData.from_json(raw_log),
                        )
                yield tuple(logs)

    async def initialize(self) -> None:
        level = await self.get_head_level()

        if not level:
            raise DatasourceError('Archive is not ready yet', self.name)

        self.set_sync_level(None, level)

    async def get_head_level(self) -> int:
        response = await self.request('get', 'height')
        return cast(int, response.get('height', 0))
