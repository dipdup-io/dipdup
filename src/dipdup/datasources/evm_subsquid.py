import zipfile
from io import BytesIO
from typing import Any
from typing import AsyncIterator
from typing import TypedDict
from typing import cast

import pyarrow.ipc  # type: ignore[import]
from typing_extensions import NotRequired

from dipdup.config import HttpConfig
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

    # NOTE: Realtime subscriptions are covered by EvmNodeDatasource
    async def run(self) -> None:
        pass

    async def subscribe(self) -> None:
        pass

    async def iter_event_logs(
        self,
        addresses: set[str],
        topics: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[SubsquidEventData, ...]]:
        current_level = first_level

        while current_level <= last_level:
            query: Query = {
                'logs': [
                    {
                        'address': list(addresses or ()),
                        'topics': [list(topics or ())],
                        'fieldSelection': _log_fields,
                    }
                ],
                'fromBlock': current_level,
                'toBlock': last_level,
            }

            response: dict[str, Any] = await self.request(
                'post',
                url='query',
                json=query,
            )

            current_level = response['nextBlock']
            sync_level = response['archiveHeight']
            self.set_sync_level(None, sync_level)

            logs: list[SubsquidEventData] = []
            for level in response['data']:
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
