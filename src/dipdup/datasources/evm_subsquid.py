import asyncio
import zipfile
from collections import defaultdict
from collections import deque
from collections.abc import AsyncIterator
from copy import copy
from io import BytesIO
from typing import Any
from typing import cast

import pyarrow.ipc  # type: ignore[import-untyped]

from dipdup.config import HttpConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import Datasource
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.http import safe_exceptions
from dipdup.models.evm_subsquid import FieldSelection
from dipdup.models.evm_subsquid import LogRequest
from dipdup.models.evm_subsquid import Query
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.models.evm_subsquid import SubsquidTransactionData
from dipdup.models.evm_subsquid import TransactionRequest

LOG_FIELDS: FieldSelection = {
    'block': {
        'timestamp': True,
    },
    'log': {
        'logIndex': True,
        'transactionIndex': True,
        'transactionHash': True,
        'address': True,
        'data': True,
        'topics': True,
    },
}
TRANSACTION_FIELDS: FieldSelection = {
    'block': {
        'timestamp': True,
    },
    'transaction': {
        'chainId': True,
        'contractAddress': True,
        'cumulativeGasUsed': True,
        'effectiveGasPrice': True,
        'from': True,
        'gasPrice': True,
        'gas': True,
        'gasUsed': True,
        'hash': True,
        'input': True,
        'maxFeePerGas': True,
        'maxPriorityFeePerGas': True,
        'nonce': True,
        'r': True,
        'sighash': True,
        'status': True,
        's': True,
        'to': True,
        'transactionIndex': True,
        'type': True,
        'value': True,
        'v': True,
        'yParity': True,
    },
}


def unpack_data(content: bytes) -> dict[str, list[dict[str, Any]]]:
    """Extract data from Subsquid zip+pyarrow archives"""
    data = {}
    with zipfile.ZipFile(BytesIO(content), 'r') as arch:
        for item in arch.filelist:
            with arch.open(item) as f, pyarrow.ipc.open_stream(f) as reader:
                table: pyarrow.Table = reader.read_all()
                data[item.filename] = table.to_pylist()
    return data


class _SubsquidWorker(Datasource[Any]):
    async def run(self) -> None:
        raise FrameworkException('Subsquid worker datasource should not be run')

    async def query(self, query: Query) -> list[dict[str, Any]]:
        self._logger.debug('Worker query: %s', query)
        response = await self.request(
            'post',
            url='',
            json=query,
        )
        return cast(list[dict[str, Any]], response)


class SubsquidDatasource(IndexDatasource[SubsquidDatasourceConfig]):
    _default_http_config = HttpConfig(
        polling_interval=1.0,
    )

    def __init__(self, config: SubsquidDatasourceConfig) -> None:
        super().__init__(config, False)

    async def run(self) -> None:
        if self._config.node:
            return
        # NOTE: If node datasource is missing, just poll API in reasonable intervals.
        while True:
            await asyncio.sleep(self._http_config.polling_interval)
            await self.initialize()

    async def subscribe(self) -> None:
        pass

    # FIXME: Heavily copy-pasted from `HTTPGateway._retry_request`
    async def query_worker(self, query: Query, current_level: int) -> list[dict[str, Any]]:
        retry_sleep = self._http_config.retry_sleep
        attempt = 1
        last_attempt = self._http_config.retry_count + 1

        while True:
            try:
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

    async def iter_event_logs(
        self,
        topics: tuple[tuple[str | None, str], ...],
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
            query: Query = {
                'logs': log_request,
                'fields': LOG_FIELDS,
                'fromBlock': current_level,
                'toBlock': last_level,
            }
            response = await self.query_worker(query, current_level)

            for level_item in response:
                current_level = level_item['header']['number'] + 1
                logs: deque[SubsquidEventData] = deque()
                for raw_log in level_item['logs']:
                    logs.append(
                        SubsquidEventData.from_json(
                            event_json=raw_log,
                            header=level_item['header'],
                        ),
                    )
                yield tuple(logs)

    async def iter_transactions(
        self,
        first_level: int,
        last_level: int,
        filters: tuple[TransactionRequest, ...],
    ) -> AsyncIterator[tuple[SubsquidTransactionData, ...]]:
        current_level = first_level

        while current_level <= last_level:
            query: Query = {
                'fields': TRANSACTION_FIELDS,
                'fromBlock': current_level,
                'toBlock': last_level,
                'transactions': list(filters),
            }
            response = await self.query_worker(query, current_level)

            for level_item in response:
                current_level = level_item['header']['number'] + 1
                transactions: deque[SubsquidTransactionData] = deque()
                for raw_transaction in level_item['transactions']:
                    transaction = SubsquidTransactionData.from_json(
                        transaction_json=raw_transaction,
                        header=level_item['header'],
                    )
                    # NOTE: `None` falue is for chains and block ranges not compliant with the post-Byzantinum
                    # hard fork EVM specification (e.g. before 4.370,000 on Ethereum).
                    if transaction.status != 0:
                        transactions.append(transaction)
                yield tuple(transactions)

    async def initialize(self) -> None:
        level = await self.get_head_level()

        if not level:
            raise DatasourceError('Subsquid is not ready yet', self.name)

        self.set_sync_level(None, level)

    async def get_head_level(self) -> int:
        response = await self.request('get', 'height')
        return int(response)

    async def _get_worker(self, level: int) -> _SubsquidWorker:
        worker_url = (
            await self._http.request(
                'get',
                f'{self._config.url}/{level}/worker',
            )
        ).decode()

        worker_config = copy(self._config)
        worker_config.url = worker_url
        if not worker_config.http:
            worker_config.http = self._default_http_config

        # NOTE: Fail immediately; retries are handled one level up
        worker_config.http.retry_count = 0

        return _SubsquidWorker(worker_config)
