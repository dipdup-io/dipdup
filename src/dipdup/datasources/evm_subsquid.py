import zipfile
from io import BytesIO
from typing import Any
from typing import TypedDict

import aiohttp
import pyarrow.ipc  # type: ignore[import]
from typing_extensions import NotRequired

from dipdup.config import HttpConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.http import _HTTPGateway
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.models.evm_subsquid import SubsquidMessageType

FieldMap = dict[str, bool]


class FieldSelection(TypedDict):
    block: NotRequired[FieldMap]
    transaction: NotRequired[FieldMap]
    log: NotRequired[FieldMap]


class LogFilter(TypedDict):
    address: NotRequired[list[str]]
    topic0: NotRequired[list[str]]


class TxFilter(TypedDict):
    to: NotRequired[list[str]]
    sighash: NotRequired[list[str]]


class Query(TypedDict):
    fields: NotRequired[FieldSelection]
    logs: NotRequired[list[LogFilter]]
    transactions: NotRequired[list[TxFilter]]
    fromBlock: NotRequired[int]
    toBlock: NotRequired[int]


_log_fields: FieldSelection = {
    'log': {
        'topics': True,
        'data': True,
    },
}


# _block_fields: FieldSelection = {
#     'block': {
#         'number': True,
#         'hash': True,
#         'parentHash': True,
#     },
# }

# def dump(
#         archive_url: str,
#         query: Query,
#         first_block: int,
#         last_block: int
# ) -> None:
#     assert 0 <= first_block <= last_block

#     query = dict(query)  # copy query to mess with it later
#     next_block = first_block

#     while next_block <= last_block:
#         # FIXME: retries for 503, 504, 502 and network failures
#         #        are required for a sequence of 2 queries below

#         res = requests.get(f'{archive_url}/{next_block}/worker')
#         res.raise_for_status()
#         worker_url = res.text

#         query['fromBlock'] = next_block
#         query['toBlock'] = last_block
#         res = requests.post(worker_url, json=query)
#         res.raise_for_status()

#         last_processed_block = int(res.headers['x-sqd-last-processed-block'])
#         print(f'processed data from block {next_block} to {last_processed_block}')
#         next_block = last_processed_block + 1

#         if res.status_code == 200:  # Might also get 204, if nothing were found at the current round
#             unpack_data(res.content)


def unpack_data(content: bytes) -> dict[str, list[dict[str, Any]]]:
    data = {}
    with zipfile.ZipFile(BytesIO(content), 'r') as arch:
        for item in arch.filelist:  # The set of files depends on requested data
            with arch.open(item) as f, pyarrow.ipc.open_stream(f) as reader:
                table: pyarrow.Table = reader.read_all()
                data[item.filename] = table.to_pylist()
    return data


# Notes:

# At the moment archive router doesn't expose information about the height of archived data
# (because it doesn't always know it).

# Attempt to request data beyond archived height leads to HTTP 503.
# The same error is returned in case of any temporal service unavailability, e.g. due upgrades.

# The suggestion is to check the chain height at the start of processing via online data source,
# and if we get HTTP 503 not far away from the head, then to switch to online data source,
# otherwise to keep retrying.

# We'll try to do something about that quirk later.


class SubsquidDatasource(IndexDatasource[SubsquidDatasourceConfig]):
    _default_http_config = HttpConfig()

    async def run(self) -> None:
        pass

    async def subscribe(self) -> None:
        pass

    async def get_event_logs(
        self,
        addresses: set[str] | None,
        topics: set[str] | None,
        first_level: int,
        last_level: int,
    ) -> tuple[SubsquidEventData, ...]:
        query: Query = {
            'fields': _log_fields,
            'logs': [
                {
                    'address': list(addresses or ()),
                    'topic0': list(topics or ()),
                }
            ],
            'fromBlock': first_level,
            'toBlock': last_level,
        }

        worker_url = await self.request('get', f'{first_level}/worker')
        worker_http = _HTTPGateway(
            url=worker_url,
            config=self._http_config,
        )
        async with worker_http:
            response: aiohttp.ClientResponse = await worker_http._request(
                'post',
                worker_url,
                1,
                True,
                json=query,
            )

            # FIXME: Not used yet
            _last_processed_block = int(response.headers['x-sqd-last-processed-block'])  # noqa: F841
            data = unpack_data(await response.read())
            raw_logs = data.get(SubsquidMessageType.logs.value, [])

        return tuple(
            SubsquidEventData(
                level=raw_log['block_number'],
                **raw_log,
            )
            for raw_log in raw_logs
        )
