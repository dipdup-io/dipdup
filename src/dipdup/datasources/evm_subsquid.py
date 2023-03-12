import asyncio
import zipfile
from io import BytesIO
from typing import Any
from typing import AsyncIterator
from typing import TypedDict

import pyarrow.ipc  # type: ignore[import]
from typing_extensions import NotRequired

from dipdup.config import HttpConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.models.evm_subsquid import SubsquidEventData

FieldMap = dict[str, bool]


class FieldSelection(TypedDict):
    block: NotRequired[FieldMap]
    transaction: NotRequired[FieldMap]
    log: NotRequired[FieldMap]


class LogFilter(TypedDict):
    address: NotRequired[list[str]]
    topics: NotRequired[list[list[str]]]
    fieldSelection: NotRequired[FieldSelection]


class TxFilter(TypedDict):
    to: NotRequired[list[str]]
    sighash: NotRequired[list[str]]


class Query(TypedDict):
    logs: NotRequired[list[LogFilter]]
    transactions: NotRequired[list[TxFilter]]
    fromBlock: NotRequired[int]
    toBlock: NotRequired[int]


_log_fields: FieldSelection = {
    'log': {
        'address': True,
        'blockNumber': True,
        'data': True,
        'topics': True,
    },
}


def unpack_data(content: bytes) -> dict[str, list[dict[str, Any]]]:
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
        # FIXME: No true realtime yet
        while True:
            await asyncio.sleep(1)
            await self.update_head()

    async def subscribe(self) -> None:
        pass

    async def add_index(self, index_config: ResolvedIndexConfigU) -> None:
        """Register index config in internal mappings and matchers. Find and register subscriptions."""
        for subscription in index_config.subscriptions:
            self._subscriptions.add(subscription)

    async def iter_event_logs(
        self,
        addresses: set[str],
        topics: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[SubsquidEventData, ...]]:
        current_level = first_level

        async def _fetch() -> AsyncIterator[tuple[SubsquidEventData, ...]]:
            query: Query = {
                'logs': [
                    {
                        'address': list(addresses or ()),
                        'topics': [list(topics or ())],
                        'fieldSelection': _log_fields,
                    }
                ],
                'fromBlock': first_level,
                'toBlock': last_level,
            }

            response: dict[str, Any] = await self.request(
                'post',
                url='query',
                json=query,
            )

            nonlocal current_level
            current_level = response['nextBlock']
            await self.update_head(response['archiveHeight'])

            for level in response['data']:
                logs: list[SubsquidEventData] = []
                for transaction in level:
                    for raw_log in transaction['logs']:
                        logs.append(
                            SubsquidEventData(
                                address=raw_log['address'],
                                data=raw_log['data'],
                                topics=raw_log['topics'],
                                level=raw_log['blockNumber'],
                            )
                        )
                yield tuple(logs)

        while current_level <= last_level:
            async for level_logs in _fetch():
                yield level_logs

    async def initialize(self) -> None:
        await self.update_head()

    async def update_head(self, level: int | None = None) -> None:
        if level is None:
            response = await self.request('get', 'height')
            level = response.get('height')

        if level is None:
            raise DatasourceError('Archive is not ready yet', self.name)
        self.set_sync_level(None, level)
