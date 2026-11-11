from collections import defaultdict
from collections import deque
from collections.abc import AsyncIterator

from dipdup.config.evm_subsquid import EvmSubsquidDatasourceConfig
from dipdup.datasources._subsquid import AbstractSubsquidDatasource
from dipdup.datasources._subsquid import AbstractSubsquidWorker
from dipdup.datasources._subsquid import SubsquidDatasourceConfigT
from dipdup.datasources._subsquid import _ArchiveTransport
from dipdup.models.evm import EvmEventData
from dipdup.models.evm import EvmTransactionData
from dipdup.models.evm_subsquid import FieldSelection
from dipdup.models.evm_subsquid import LogRequest
from dipdup.models.evm_subsquid import Query
from dipdup.models.evm_subsquid import TransactionRequest

_LOG_FIELDS: FieldSelection = {
    'block': {
        # NOTE: Portal returns only requested block fields; v2.archive always included
        # number/hash, so request them explicitly — the parser needs all three.
        'number': True,
        'hash': True,
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
_TRANSACTION_FIELDS: FieldSelection = {
    'block': {
        # NOTE: see _LOG_FIELDS — Portal only returns requested block fields.
        'number': True,
        'hash': True,
        'timestamp': True,
    },
    'transaction': {
        # 'accessList': True,
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


class _EvmSubsquidWorker(AbstractSubsquidWorker[Query]):
    pass


class _AbstractEvmSubsquidDatasource(AbstractSubsquidDatasource[SubsquidDatasourceConfigT, Query]):
    """EVM chain logic (query build + parse) shared by the v2.archive and Portal transports."""

    async def iter_events(
        self,
        topics: tuple[tuple[str | None, str], ...],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[EvmEventData, ...]]:
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
                'fields': _LOG_FIELDS,
                'fromBlock': current_level,
                'toBlock': last_level,
            }
            response = await self.query_worker(query, current_level)

            # NOTE: Portal's `/finalized-stream` returns an empty body once no blocks in
            # [current_level, last_level] match the query. `current_level` only advances inside
            # the loop below, so without this guard an empty response re-queries forever.
            if not response:
                break

            for level_item in response:
                current_level = level_item['header']['number'] + 1
                logs: deque[EvmEventData] = deque()
                for raw_log in level_item['logs']:
                    logs.append(
                        EvmEventData.from_subsquid_json(
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
    ) -> AsyncIterator[tuple[EvmTransactionData, ...]]:
        current_level = first_level
        transaction_request = list(filters)

        while current_level <= last_level:
            query: Query = {
                'fields': _TRANSACTION_FIELDS,
                'fromBlock': current_level,
                'toBlock': last_level,
                'transactions': transaction_request,
            }
            response = await self.query_worker(query, current_level)

            # NOTE: see `iter_events` — an empty Portal stream means the range is exhausted;
            # break instead of re-querying the same range forever.
            if not response:
                break

            for level_item in response:
                current_level = level_item['header']['number'] + 1
                transactions: deque[EvmTransactionData] = deque()
                for raw_transaction in level_item['transactions']:
                    transaction = EvmTransactionData.from_subsquid_json(
                        transaction_json=raw_transaction,
                        header=level_item['header'],
                    )
                    # NOTE: `None` falue is for chains and block ranges not compliant with the post-Byzantinum
                    # hard fork EVM specification (e.g. before 4.370,000 on Ethereum).
                    if transaction.status != 0:
                        transactions.append(transaction)
                yield tuple(transactions)


class EvmSubsquidDatasource(
    _AbstractEvmSubsquidDatasource[EvmSubsquidDatasourceConfig],
    _ArchiveTransport[EvmSubsquidDatasourceConfig, Query],
):
    def __init__(self, config: EvmSubsquidDatasourceConfig) -> None:
        super().__init__(config)

    async def _get_worker(self, level: int) -> _EvmSubsquidWorker:
        return _EvmSubsquidWorker(await self._fetch_worker(level))
