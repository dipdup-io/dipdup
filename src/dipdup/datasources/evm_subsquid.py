# import zipfile
# from io import BytesIO
from typing import TypedDict

# import pyarrow.ipc
# from pydantic.dataclasses import dataclass
from typing_extensions import NotRequired

from dipdup.config import HttpConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import IndexDatasource

DEFAULT_QUERY = (
    {
        'logs': [
            {
                'address': ['0x2e645469f354bb4f5c8a05b3b30a929361cf77ec'],
                'topic0': [
                    '0x9ab3aefb2ba6dc12910ac1bce4692cf5c3c0d06cff16327c64a3ef78228b130b',
                    '0x76571b7a897a1509c641587568218a290018fbdc8b9a724f17b77ff0eec22c0c',
                ],
            }
        ],
        'fields': {
            'block': {
                'number': True,
                'hash': True,
                'parentHash': True,
            },
            'log': {'topics': True, 'data': True},
        },
    },
)


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


# def unpack_data(content: bytes):
#     with zipfile.ZipFile(BytesIO(content), 'r') as arch:
#         for item in arch.filelist:  # The set of files depends on requested data
#             print()
#             print(item.filename.upper())
#             with arch.open(item) as f, \
#                 pyarrow.ipc.open_stream(f) as reader:
#                 table: pyarrow.Table = reader.read_all()
#                 # checkout https://arrow.apache.org/docs/python/data.html#tables
#                 # for what can be done with pyarrow tables
#                 print(table.to_pylist())
#             print()


# if __name__ == '__main__':
#     dump(
#         'https://v2.archive.subsquid.io/network/ethereum-mainnet',
#         query=
#         first_block=5_000_000,
#         last_block=8_500_000
#     )


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

    # async def get_logs(
    #     self,
    #     field: str,
    #     addresses: set[str] | None,
    #     code_hashes: set[int] | None,
    #     first_level: int | None = None,
    #     last_level: int | None = None,
    #     offset: int | None = None,
    #     limit: int | None = None,
    # ) -> tuple[TzktOperationData, ...]:
    #     params = self._get_request_params(
    #         first_level,
    #         last_level,
    #         offset,
    #         limit,
    #         TRANSACTION_OPERATION_FIELDS,
    #         cursor=True,
    #         status='applied',
    #     )
