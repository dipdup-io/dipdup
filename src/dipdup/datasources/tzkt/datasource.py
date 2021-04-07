import asyncio
import logging
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from signalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from signalrcore.hub_connection_builder import HubConnectionBuilder  # type: ignore
from signalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from tortoise.transactions import in_transaction

from dipdup.config import ROLLBACK_HANDLER, OperationHandlerConfig, OperationIndexConfig
from dipdup.datasources.tzkt.cache import OperationCache
from dipdup.datasources.tzkt.enums import TzktMessageType
from dipdup.models import HandlerContext, OperationData, State

TZKT_HTTP_REQUEST_LIMIT = 10000
TZKT_HTTP_REQUEST_SLEEP = 1


class TzktDatasource:
    def __init__(
        self,
        url: str,
        operation_index_configs: List[OperationIndexConfig],
    ):
        super().__init__()
        self._url = url.rstrip('/')
        self._operation_index_configs = {config.contract: config for config in operation_index_configs}
        self._synchronized = asyncio.Event()
        self._callback_lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)
        self._subscriptions: Dict[str, List[str]] = {}
        self._subscriptions_registered: List[Tuple[str, str]] = []
        self._sync_events = {config.state.index_name: asyncio.Event() for config in operation_index_configs}
        self._client: Optional[BaseHubConnection] = None
        self._caches = {config.contract: OperationCache(config, config.state.level) for config in operation_index_configs}

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
        for config in self._operation_index_configs.values():
            await self.add_subscription(config.contract)

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

        self._logger.info('Fetching operations prior to level %s', last_level)
        for index_config in self._operation_index_configs.values():

            sync_event = self._sync_events[index_config.state.index_name]
            level = index_config.state.level or 0
            if level == last_level:
                sync_event.set()
                continue

            operations = []
            offset = 0

            while True:
                fetched_operations = await self._fetch_operations(index_config.contract, offset, level, last_level)
                operations += fetched_operations

                while True:
                    for i in range(len(operations) - 1):
                        if operations[i]['level'] != operations[i + 1]['level']:
                            await _process_operations(index_config.contract, operations[: i + 1])
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
                await _process_operations(index_config.contract, operations)

            sync_event.set()

        self._logger.info('Synchronization finished')
        self._synchronized.set()

    async def fetch_jsonschemas(self, address: str) -> Dict[str, Any]:
        self._logger.info('Fetching jsonschemas for address `%s', address)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=f'{self._url}/v1/contracts/{address}/interface',
            ) as resp:
                jsonschemas = await resp.json()
        self._logger.debug(jsonschemas)
        return jsonschemas

    async def on_operation_message(
        self,
        message: List[Dict[str, Any]],
        address: str,
        sync=False,
    ) -> None:
        self._logger.info('Got operation message on %s', address)
        self._logger.debug('%s', message)
        index_config = self._operation_index_configs[address]
        for item in message:
            message_type = TzktMessageType(item['type'])

            if message_type == TzktMessageType.STATE:
                level = item['state']
                self._logger.info('Got state message, current level %s, index level %s', level, index_config.state.level)
                await self.fetch_operations(level)

            elif message_type == TzktMessageType.DATA:
                sync_event = self._sync_events[index_config.state.index_name]
                if not sync and not sync_event.is_set():
                    self._logger.info('Waiting until synchronization is complete')
                    await sync_event.wait()
                    self._logger.info('Synchronization is complete, processing websocket message')

                self._logger.info('Acquiring callback lock')
                async with self._callback_lock:
                    for operation_json in item['data']:
                        operation = self.convert_operation(operation_json)
                        if operation.type != 'transaction':
                            continue
                        await self._caches[address].add(operation)

                    async with in_transaction():
                        last_level = await self._caches[address].process(self.on_operation_match)
                        index_config.state.level = last_level  # type: ignore
                        await index_config.state.save()

            elif message_type == TzktMessageType.REORG:
                self._logger.info(f'Got reorg message, calling `%s` handler', ROLLBACK_HANDLER)
                from_level = self._operation_index_configs[address].state.level
                to_level = item['state']
                await self._operation_index_configs[address].rollback_fn(from_level, to_level)

            else:
                self._logger.warning('%s is not supported', message_type)

    async def add_subscription(self, address: str, types: Optional[List[str]] = None) -> None:
        if types is None:
            types = ['transaction']
        if address not in self._subscriptions:
            self._subscriptions[address] = types

    async def on_operation_match(
        self,
        index_config: OperationIndexConfig,
        handler_config: OperationHandlerConfig,
        matched_operations: List[OperationData],
        operations: List[OperationData],
    ):
        args = []
        for pattern_config, operation in zip(handler_config.pattern, matched_operations):

            parameter_type = pattern_config.parameter_type_cls
            parameter = parameter_type.parse_obj(operation.parameter_json)

            context = HandlerContext(
                data=operation,
                parameter=parameter,
            )
            args.append(context)

        await handler_config.callback_fn(*args, operations, index_config.template_values)

    @classmethod
    def convert_operation(cls, operation_json: Dict[str, Any]) -> OperationData:
        return OperationData(
            type=operation_json['type'],
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=operation_json['timestamp'],
            block=operation_json['block'],
            hash=operation_json['hash'],
            counter=operation_json['counter'],
            sender_address=operation_json['sender']['address'],
            gas_limit=operation_json['gasLimit'],
            gas_used=operation_json['gasUsed'],
            storage_limit=operation_json['storageLimit'],
            storage_used=operation_json['storageUsed'],
            baker_fee=operation_json['bakerFee'],
            storage_fee=operation_json['storageFee'],
            allocation_fee=operation_json['allocationFee'],
            target_address=operation_json['target']['address'],
            amount=operation_json['amount'],
            status=operation_json['status'],
            has_internals=operation_json['hasInternals'],
            sender_alias=operation_json['sender'].get('alias'),
            nonce=operation_json.get('nonce'),
            target_alias=operation_json['target'].get('alias'),
            entrypoint=operation_json.get('parameter', {}).get('entrypoint'),
            parameter_json=operation_json.get('parameter', {}).get('value'),
            initiator_address=operation_json.get('initiator', {}).get('address'),
            parameter=operation_json.get('parameters'),
        )
