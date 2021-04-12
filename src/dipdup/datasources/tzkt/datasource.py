import asyncio
import json
import logging
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
from aiosignalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from aiosignalrcore.hub_connection_builder import HubConnectionBuilder  # type: ignore
from aiosignalrcore.messages.completion_message import CompletionMessage  # type: ignore
from aiosignalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from tortoise.transactions import in_transaction

from dipdup.config import ROLLBACK_HANDLER, BigmapdiffIndexConfig, BlockIndexConfig, OperationHandlerConfig, OperationIndexConfig
from dipdup.datasources.tzkt.cache import OperationCache
from dipdup.datasources.tzkt.enums import TzktMessageType
from dipdup.models import HandlerContext, OperationContext, OperationData, State

TZKT_HTTP_REQUEST_LIMIT = 10000
TZKT_HTTP_REQUEST_SLEEP = 1
OPERATION_FIELDS = (
    "type",
    "id",
    "level",
    "timestamp",
    # "block",
    "hash",
    "counter",
    "initiator",
    "sender",
    "nonce",
    "gasLimit",
    "gasUsed",
    "storageLimit",
    "storageUsed",
    "bakerFee",
    "storageFee",
    "allocationFee",
    "target",
    "amount",
    "parameter",
    "storage",
    "status",
    "errors",
    "hasInternals",
    # "quote",
    "parameters",
    "bigmaps,",
)


class TzktDatasource:
    def __init__(self, url: str):
        super().__init__()
        self._url = url.rstrip('/')
        self._operation_index_configs: Dict[str, OperationIndexConfig] = {}
        self._synchronized = asyncio.Event()
        self._callback_lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)
        self._subscriptions: Dict[str, List[str]] = {}
        self._subscriptions_registered: List[Tuple[str, str]] = []
        self._sync_events: Dict[str, asyncio.Event] = {}
        self._client: Optional[BaseHubConnection] = None
        self._caches: Dict[str, OperationCache] = {}

    def add_index(self, config: Union[OperationIndexConfig, BigmapdiffIndexConfig, BlockIndexConfig]):
        if isinstance(config, OperationIndexConfig):
            self._logger.info(f'Adding index "{config.state.index_name}"')
            self._operation_index_configs[config.contract_config.address] = config
            self._sync_events[config.state.index_name] = asyncio.Event()
            self._caches[config.contract_config.address] = OperationCache(config, config.state.level)
            if len(self._operation_index_configs) > 1:
                self._logger.warning('Using more than one operation index. Be careful, indexing is not atomic.')
        else:
            raise NotImplementedError(f'Index kind `{config.kind}` is not supported')

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
            self._client.on_error(self.on_error)

        return self._client

    async def start(self):
        self._logger.info('Starting datasource')
        for operation_index_config in self._operation_index_configs.values():
            await self.add_subscription(operation_index_config.contract)

            latest_block = await self.get_latest_block()
            current_level = latest_block['level']
            state_level = operation_index_config.state.level
            if current_level != state_level:
                await self.fetch_operations(current_level, initial=True)

        self._logger.info('Starting websocket client')
        await self._get_client().start()

    async def stop(self):
        ...

    async def on_connect(self):
        self._logger.info('Connected to server')
        for contract, subscriptions in self._subscriptions.items():
            await self.subscribe_to_operations(contract.address, subscriptions)

    def on_error(self, message: CompletionMessage):
        raise Exception(message.error)

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
                    "select": ','.join(OPERATION_FIELDS),
                },
            ) as resp:
                operations = await resp.json()
        self._logger.info('%s operations fetched', len(operations))
        self._logger.debug(operations)
        return operations

    async def fetch_operations(self, last_level: int, initial: bool = False) -> None:
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

            operations = []
            offset = 0

            while True:
                fetched_operations = await self._fetch_operations(index_config.contract_config.address, offset, level, last_level)
                operations += fetched_operations

                while True:
                    for i in range(len(operations) - 1):
                        if operations[i]['level'] != operations[i + 1]['level']:
                            await _process_operations(index_config.contract_config.address, operations[: i + 1])
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
                await _process_operations(index_config.contract_config.address, operations)

            if not initial:
                sync_event.set()

        if not initial:
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
                        if operation.status != 'applied':
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
        handler_context = HandlerContext(
            operations=operations,
            template_values=index_config.template_values,
        )
        args: List[Union[OperationContext, HandlerContext]] = [handler_context]
        for pattern_config, operation in zip(handler_config.pattern, matched_operations):

            parameter_type = pattern_config.parameter_type_cls
            parameter = parameter_type.parse_obj(operation.parameter_json)

            if operation.storage:
                storage_type = pattern_config.storage_type_cls
                storage = operation.get_merged_storage(storage_type)
            else:
                storage = None

            operation_context = OperationContext(
                data=operation,
                parameter=parameter,
                storage=storage,
            )
            args.append(operation_context)

        await handler_config.callback_fn(*args)

    @classmethod
    def convert_operation(cls, operation_json: Dict[str, Any]) -> OperationData:
        return OperationData(
            # FIXME: type is null
            type=operation_json['type'] or 'transaction',
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=operation_json['timestamp'],
            block=operation_json.get('block'),
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
            entrypoint=operation_json['parameter']['entrypoint'] if operation_json.get('parameter') else None,
            parameter_json=operation_json['parameter']['value'] if operation_json.get('parameter') else None,
            initiator_address=operation_json['initiator']['address'] if operation_json.get('initiator') else None,
            parameter=operation_json.get('parameters'),
            storage=operation_json.get('storage'),
            bigmaps=operation_json.get('bigmaps'),
        )

    async def get_latest_block(self) -> Dict[str, Any]:
        self._logger.info('Fetching latest block')
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=f'{self._url}/v1/blocks',
                params={
                    "limit": 1,
                    "sort.desc": "id",
                },
            ) as resp:
                blocks = await resp.json()
        self._logger.debug(blocks)
        return blocks[0]
