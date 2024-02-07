import asyncio
import random
import time
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections import deque
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import cast

from web3 import Web3

from dipdup.config import SubsquidIndexConfigU
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.context import DipDupContext
from dipdup.datasources.evm_node import NODE_LAST_MILE
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import IndexQueueItemT
from dipdup.models.evm_subsquid import SubsquidMessageType
from dipdup.package import DipDupPackage
from dipdup.performance import metrics
from dipdup.prometheus import Metrics

IndexConfigT = TypeVar('IndexConfigT', bound=SubsquidIndexConfigU)
DatasourceT = TypeVar('DatasourceT', bound=SubsquidDatasource)


_sighashes: dict[str, str] = {}


def get_sighash(package: DipDupPackage, method: str, to: EvmContractConfig | None = None) -> str:
    """Method in config is either a full signature or a method name. We need to convert it to a sighash first."""
    key = method + (to.module_name if to else '')
    if key in _sighashes:
        return _sighashes[key]

    if {'(', ')'} <= set(method) and not to:
        _sighashes[key] = Web3.keccak(text=method).hex()[:10]
    elif to:
        _sighashes[key] = package.get_converted_abi(to.module_name)['methods'][method]['sighash']
    else:
        raise ConfigurationError('`to` field is missing; `method` is expected to be a full signature')
    return _sighashes[key]


class SubsquidIndex(
    Index[IndexConfigT, IndexQueueItemT, DatasourceT],
    ABC,
    Generic[IndexConfigT, IndexQueueItemT, DatasourceT],
    message_type=SubsquidMessageType,
):
    def __init__(
        self,
        ctx: DipDupContext,
        config: IndexConfigT,
        datasource: DatasourceT,
    ) -> None:
        super().__init__(ctx, config, datasource)

        node_field = self._config.datasource.node
        if node_field is None:
            node_field = ()
        elif isinstance(node_field, EvmNodeDatasourceConfig):
            node_field = (node_field,)
        self._node_datasources = tuple(
            self._ctx.get_evm_node_datasource(node_config.name) for node_config in node_field
        )

    @abstractmethod
    async def _synchronize_subsquid(self, sync_level: int) -> None: ...

    @abstractmethod
    async def _synchronize_node(self, sync_level: int) -> None: ...

    @abstractmethod
    def _match_level_data(
        self,
        handlers: Any,
        level_data: Any,
    ) -> deque[Any]: ...

    @abstractmethod
    async def _call_matched_handler(
        self,
        handler_config: Any,
        level_data: Any,
    ) -> None: ...

    @property
    def node_datasources(self) -> tuple[EvmNodeDatasource, ...]:
        return self._node_datasources

    def get_random_node(self) -> EvmNodeDatasource:
        if not self._node_datasources:
            raise FrameworkException('A node datasource requested, but none attached to this index')
        return random.choice(self._node_datasources)

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        sync_levels = set()
        for sub in self._config.get_subscriptions():
            sync_levels.add(self.datasource.get_sync_level(sub))
            for datasource in self.node_datasources or ():
                sync_levels.add(datasource.get_sync_level(sub))

        if None in sync_levels:
            sync_levels.remove(None)
        if not sync_levels:
            raise FrameworkException('Initialize config before starting `IndexDispatcher`')

        # NOTE: Multiple sync levels means index with new subscriptions was added in runtime.
        # NOTE: Choose the highest level; outdated realtime messages will be dropped from the queue anyway.
        return max(cast(set[int], sync_levels))

    async def get_blocks_batch(
        self,
        levels: set[int],
        full_transactions: bool = False,
    ) -> dict[int, dict[str, Any]]:
        tasks: deque[asyncio.Task[Any]] = deque()
        blocks: dict[int, Any] = {}

        async def _fetch(level: int) -> None:
            blocks[level] = await self.get_random_node().get_block_by_level(
                block_number=level,
                full_transactions=full_transactions,
            )

        for level in levels:
            tasks.append(
                asyncio.create_task(
                    _fetch(level),
                    name=f'get_block_range:{level}',
                ),
            )

        await asyncio.gather(*tasks)
        return blocks

    async def get_logs_batch(
        self,
        first_level: int,
        last_level: int,
    ) -> dict[int, list[dict[str, Any]]]:
        grouped_logs: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        logs = await self.get_random_node().get_logs(
            {
                'fromBlock': hex(first_level),
                'toBlock': hex(last_level),
            },
        )
        for log in logs:
            grouped_logs[int(log['blockNumber'], 16)].append(log)
        return grouped_logs

    async def _get_node_sync_level(self, subsquid_level: int, index_level: int) -> int | None:
        if not self.node_datasources:
            return None

        node_sync_level = await self.get_random_node().get_head_level()
        subsquid_lag = abs(node_sync_level - subsquid_level)
        subsquid_available = subsquid_level - index_level
        self._logger.info('Subsquid is %s levels behind; %s available', subsquid_lag, subsquid_available)
        if subsquid_available < NODE_LAST_MILE:
            return node_sync_level
        if self._config.node_only:
            self._logger.debug('`node_only` flag is set; using node anyway')
            return node_sync_level
        return None

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch event logs via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        levels_left = sync_level - index_level
        if levels_left <= 0:
            return

        subsquid_sync_level = await self.datasource.get_head_level()
        Metrics.set_sqd_processor_chain_height(subsquid_sync_level)
        node_sync_level = await self._get_node_sync_level(subsquid_sync_level, index_level)

        # NOTE: Fetch last blocks from node if there are not enough realtime messages in queue
        if node_sync_level:
            sync_level = min(sync_level, node_sync_level)
            self._logger.debug('Using node datasource; sync level: %s', sync_level)
            await self._synchronize_node(sync_level)
        else:
            sync_level = min(sync_level, subsquid_sync_level)
            await self._synchronize_subsquid(sync_level)

        await self._exit_sync_state(sync_level)

    async def _process_level_data(
        self,
        level_data: Any,
        sync_level: int,
    ) -> None:
        if not level_data:
            return

        batch_level = level_data[0].level
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing data of level %s', batch_level)
        started_at = time.time()
        matched_handlers = self._match_level_data(self._config.handlers, level_data)

        total_matched = len(matched_handlers)
        Metrics.set_index_handlers_matched(total_matched)
        metrics[f'{self.name}:handlers_matched'] += total_matched
        metrics[f'{self.name}:time_in_matcher'] += (time.time() - started_at) / 60

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self._update_state(level=batch_level)
            return

        started_at = time.time()
        async with self._ctx.transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, data in matched_handlers:
                await self._call_matched_handler(handler_config, data)
            await self._update_state(level=batch_level)
        metrics[f'{self.name}:time_in_callbacks'] += (time.time() - started_at) / 60
