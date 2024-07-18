from collections import deque
from collections.abc import AsyncIterator
from typing import Any

from dipdup.config.starknet_subsquid import StarknetSubsquidDatasourceConfig
from dipdup.datasources._subsquid import AbstractSubsquidDatasource
from dipdup.datasources._subsquid import AbstractSubsquidWorker
from dipdup.models.starknet import StarknetEventData
from dipdup.models.starknet import StarknetTransactionData
from dipdup.models.starknet_subsquid import EventRequest
from dipdup.models.starknet_subsquid import FieldSelection
from dipdup.models.starknet_subsquid import Query
from dipdup.models.starknet_subsquid import TransactionRequest

_TRANSACTION_FIELDS: FieldSelection = {
    'block': {
        'timestamp': True,
    },
    'transaction': {
        'transactionHash': True,
        'contractAddress': True,
        'entryPointSelector': True,
        'calldata': True,
        'maxFee': True,
        'type': True,
        'senderAddress': True,
        'version': True,
        'signature': True,
        'nonce': True,
        'classHash': True,
        'compiledClassHash': True,
        'contractAddressSalt': True,
        'constructorCalldata': True,
    },
}

_EVENT_FIELDS: FieldSelection = {
    'block': {
        'timestamp': True,
    },
    'event': {
        'fromAddress': True,
        'keys': True,
        'data': True,
    },
    'transaction': {
        'transactionHash': True,
    },
}


class _StarknetSubsquidWorker(AbstractSubsquidWorker[Query]):
    pass


class StarknetSubsquidDatasource(AbstractSubsquidDatasource[StarknetSubsquidDatasourceConfig, Query]):

    async def _get_worker(self, level: int) -> _StarknetSubsquidWorker:
        return _StarknetSubsquidWorker(await self._fetch_worker(level))

    async def query_worker(self, query: Query, current_level: int) -> list[dict[str, Any]]:
        return await super().query_worker(query, current_level)

    async def iter_events(
        self,
        first_level: int,
        last_level: int,
        filters: tuple[EventRequest, ...],
    ) -> AsyncIterator[tuple[StarknetEventData, ...]]:
        current_level = first_level

        for f in filters:
            f['transaction'] = True

        while current_level <= last_level:
            query: Query = {
                'fields': _EVENT_FIELDS,
                'fromBlock': current_level,
                'toBlock': last_level,
                'events': list(filters),
                'type': 'starknet',
            }
            response = await self.query_worker(query, current_level)

            for level_item in response:
                current_level = level_item['header']['number'] + 1
                logs: deque[StarknetEventData] = deque()
                transaction_index = 0
                for raw_event in level_item['events']:
                    # TODO: should we raise more meaningful error if subsquid data is not correct?
                    while (
                        level_item['transactions'][transaction_index]['transactionIndex']
                        != raw_event['transactionIndex']
                    ):
                        transaction_index += 1
                    logs.append(
                        StarknetEventData.from_subsquid_json(
                            event_json=raw_event,
                            transaction_json=level_item['transactions'][transaction_index],
                            header=level_item['header'],
                        ),
                    )
                yield tuple(logs)

    async def iter_transactions(
        self,
        first_level: int,
        last_level: int,
        filters: tuple[TransactionRequest, ...],
    ) -> AsyncIterator[tuple[StarknetTransactionData, ...]]:
        current_level = first_level

        while current_level <= last_level:
            query: Query = {
                'fields': _TRANSACTION_FIELDS,
                'fromBlock': current_level,
                'toBlock': last_level,
                'transactions': list(filters),
                'type': 'starknet',
            }
            response = await self.query_worker(query, current_level)

            for level_item in response:
                current_level = level_item['header']['number'] + 1
                transactions: deque[StarknetTransactionData] = deque()
                # NOTE: level_item don't have 'transactions' when no filter is applied
                for raw_transaction in level_item['transactions']:
                    transaction = StarknetTransactionData.from_subsquid_json(
                        transaction_json=raw_transaction,
                        header=level_item['header'],
                    )
                    transactions.append(transaction)
                yield tuple(transactions)
