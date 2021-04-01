import asyncio
import logging
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from cattrs_extras.converter import Converter
from signalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from signalrcore.hub_connection_builder import HubConnectionBuilder  # type: ignore
from signalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from tortoise.transactions import in_transaction

from pytezos_dapps.config import OperationHandlerConfig, OperationIndexConfig
from pytezos_dapps.datasources.tzkt.cache import OperationCache
from pytezos_dapps.datasources.tzkt.enums import TzktMessageType
from pytezos_dapps.models import HandlerContext, OperationData, State, Transaction

TZKT_HTTP_REQUEST_LIMIT = 10000
TZKT_HTTP_REQUEST_SLEEP = 1


class TzktDatasource:
    def __init__(self, url: str, index_config: OperationIndexConfig, state: State):
        super().__init__()
        self._url = url
        self._index_config = index_config
        self._state = state
        self._synchronized = asyncio.Event()
        self._callback_lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)
        self._subscriptions: Dict[str, List[str]] = {}
        self._subscriptions_registered: List[Tuple[str, str]] = []
        self._client: Optional[BaseHubConnection] = None
        self._cache = OperationCache(index_config, self._state.level)

    def _get_client(self) -> BaseHubConnection:
        if self._client is None:
            self._logger.info('Creating websocket client')
            self._client = (
                HubConnectionBuilder()
                .with_url(self._url + '/v1/events')
                .with_automatic_reconnect(
                    {
                        "type": "raw",
                        "keep_alive_interval": 10,
                        "reconnect_interval": 5,
                        "max_attempts": 5,
                    }
                )
            ).build()
            self._client.on_open(self.on_connect)

        return self._client

    async def start(self):
        self._logger.info('Starting datasource')
        await self.add_subscription(self._index_config.contract)

        self._logger.info('Starting websocket client')
        await self._get_client().start()

    async def stop(self):
        ...

    async def on_connect(self):
        self._logger.info('Connected to server')
        for address, subscriptions in self._subscriptions.items():
            await self.subscribe_to_operations(address, subscriptions)

    async def subscribe_to_operations(self, address: str, types: List[str]) -> None:
        self._logger.info('Subscribing to %s, %s', address, types)

        key = ('operations', address)
        if key not in self._subscriptions_registered:
            self._subscriptions_registered.append(key)
            self._get_client().on(
                'operations',
                partial(self.on_operation_message, address=address),
            )

        while self._get_client().transport.state != ConnectionState.connected:
            await asyncio.sleep(0.1)

        await self._get_client().send(
            'SubscribeToOperations',
            [
                {
                    'address': address,
                    'types': ','.join(types),
                }
            ],
        )

    async def _fetch_operations(self, address: str, offset: int, first_level: int, last_level: int) -> List[Dict[str, Any]]:
        self._logger.info('Fetching levels %s-%s with offset %s', first_level, last_level, offset)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=f'{self._url}/v1/operations/transactions',
                params={
                    "anyof.sender.target.initiator": address,
                    "offset": offset,
                    "limit": TZKT_HTTP_REQUEST_LIMIT,
                    "level.gt": first_level,
                    "level.le": last_level,
                },
            ) as resp:
                operations = await resp.json()
        self._logger.info('%s operations fetched', len(operations))
        self._logger.debug(operations)
        return operations

    async def fetch_operations(self, last_level: int) -> None:
        async def _process_operations(address, operations):
            self._logger.info('Processing %s operations of level %s', len(operations), operations[0]['level'])
            await self.on_operation_message(
                address=address,
                message=[
                    {
                        'type': TzktMessageType.DATA.value,
                        'data': operations,
                    },
                ],
                sync=True,
            )

        level = self._state.level or 0
        if level == last_level:
            self._synchronized.set()
            return

        self._logger.info('Fetching operations prior to level %s', last_level)
        for address in self._subscriptions:
            operations = []
            offset = 0

            while True:
                fetched_operations = await self._fetch_operations(address, offset, level, last_level)
                operations += fetched_operations

                while True:
                    for i in range(len(operations) - 1):
                        if operations[i]['level'] != operations[i + 1]['level']:
                            await _process_operations(address, operations[: i + 1])
                            operations = operations[i + 1 :]
                            break
                    else:
                        break

                if len(fetched_operations) < TZKT_HTTP_REQUEST_LIMIT:
                    break

                offset += TZKT_HTTP_REQUEST_LIMIT
                self._logger.info('Sleeping %s seconds before fetching next batch', TZKT_HTTP_REQUEST_SLEEP)
                await asyncio.sleep(TZKT_HTTP_REQUEST_SLEEP)

            if operations:
                await _process_operations(address, operations)

        self._logger.info('Synchronization finished')
        self._synchronized.set()

    async def on_operation_message(
        self,
        message: List[Dict[str, Any]],
        address: str,
        sync=False,
    ) -> None:
        self._logger.info('Got operation message on %s', address)
        self._logger.debug('%s', message)
        for item in message:
            message_type = TzktMessageType(item['type'])

            if message_type == TzktMessageType.STATE:
                level = item['state']
                self._logger.info('Got state message, current level %s, index level %s', level, self._state.level)
                await self.fetch_operations(level)

            elif message_type == TzktMessageType.DATA:
                if not sync and not self._synchronized.is_set():
                    self._logger.info('Waiting until synchronization is complete')
                    await self._synchronized.wait()
                    self._logger.info('Synchronization is complete, processing websocket message')

                self._logger.info('Acquiring callback lock')
                async with self._callback_lock:
                    for operation_json in item['data']:
                        operation = self.convert_operation(operation_json)
                        if operation.type != 'transaction':
                            continue
                        await self._cache.add(operation)

                    async with in_transaction():
                        last_level = await self._cache.process(self.on_operation_match)
                        self._state.level = last_level  # type: ignore
                        await self._state.save()

            else:
                self._logger.warning('%s is not supported', message_type)

    async def add_subscription(self, address: str, types: Optional[List[str]] = None) -> None:
        if types is None:
            types = ['transaction']
        if address not in self._subscriptions:
            self._subscriptions[address] = types

    async def on_operation_match(self, handler_config: OperationHandlerConfig, operations: List[OperationData]):
        args = []
        for pattern_config, operation in zip(handler_config.pattern, operations):
            transaction, _ = await Transaction.get_or_create(id=operation.id, block=operation.block)

            parameter_type = pattern_config.parameter_type_cls
            parameter = parameter_type.parse_obj(operation.parameter_json)

            context = HandlerContext(
                data=operation,
                transaction=transaction,
                parameter=parameter,
            )
            args.append(context)

        await handler_config.callback_fn(*args)

    @classmethod
    def convert_operation(cls, operation_json: Dict[str, Any]) -> OperationData:
        operation_json['initiator_address'] = operation_json.get('initiator', {}).get('address')
        operation_json['sender_address'] = operation_json['sender']['address']
        operation_json['sender_alias'] = operation_json['sender'].get('alias')
        operation_json['gas_limit'] = operation_json['gasLimit']
        operation_json['gas_used'] = operation_json['gasUsed']
        operation_json['storage_limit'] = operation_json['storageLimit']
        operation_json['storage_used'] = operation_json['storageUsed']
        operation_json['baker_fee'] = operation_json['bakerFee']
        operation_json['storage_fee'] = operation_json['storageFee']
        operation_json['allocation_fee'] = operation_json['allocationFee']
        operation_json['target_alias'] = operation_json['target'].get('alias')
        operation_json['target_address'] = operation_json['target']['address']
        operation_json['entrypoint'] = operation_json.get('parameter', {}).get('entrypoint')
        operation_json['parameter_json'] = operation_json.get('parameter', {}).get('value')
        operation_json['has_internals'] = operation_json['hasInternals']
        return Converter().structure(operation_json, OperationData)
