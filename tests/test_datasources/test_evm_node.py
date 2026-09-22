import asyncio
from typing import TYPE_CHECKING
from typing import Any
from unittest.mock import AsyncMock

from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.datasources.evm_node import NODE_LEVEL_TIMEOUT
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.models import MessageType
from dipdup.models.evm_node import EvmNodeHeadData
from dipdup.subscriptions.evm_node import EvmNodeHeadSubscription

if TYPE_CHECKING:
    from dipdup.datasources import IndexDatasource

# NOTE: A project with both an `evm.events` and an `evm.transactions` index on one node datasource
# holds two unequal head subscriptions, so the node opens two identical `newHeads` streams and
# announces every block twice, back to back. See `test_subscriptions.py` for the config side.
PLAIN_HEAD = EvmNodeHeadSubscription()
TRANSACTIONS_HEAD = EvmNodeHeadSubscription(transactions=True)

# NOTE: A healthy emitter loop never returns; it parks on an empty queue. So "drain it" means
# "run it until it stops making progress". Each queued head costs at most one `wait_level` sleep.
DRAIN_TIMEOUT = max(1.0, NODE_LEVEL_TIMEOUT * 20)

BLOCK_HASH = '0x' + 'ab' * 32


def _head_json(block_hash: str, level: int) -> dict[str, Any]:
    return {
        'baseFeePerGas': '0x3b9aca00',
        'difficulty': '0x0',
        'extraData': '0x',
        'gasLimit': '0x1c9c380',
        'gasUsed': '0x5208',
        'hash': block_hash,
        'logsBloom': '0x' + '00' * 256,
        'miner': '0x' + '00' * 20,
        'mixHash': '0x' + '00' * 32,
        'nonce': '0x0000000000000000',
        'number': hex(level),
        'parentHash': '0x' + '11' * 32,
        'receiptsRoot': '0x' + '22' * 32,
        'sha3Uncles': '0x' + '33' * 32,
        'stateRoot': '0x' + '44' * 32,
        'timestamp': hex(1_750_000_000 + level),
        'transactionsRoot': '0x' + '55' * 32,
    }


class Recorder:
    def __init__(self) -> None:
        self.heads: list[int] = []
        self.rollbacks: list[tuple[MessageType, int, int]] = []

    def attach(self, datasource: EvmNodeDatasource) -> None:
        async def on_head(_datasource: EvmNodeDatasource, head: EvmNodeHeadData) -> None:
            self.heads.append(head.level)

        async def on_rollback(
            _datasource: 'IndexDatasource[Any]',
            type_: MessageType,
            from_level: int,
            to_level: int,
        ) -> None:
            self.rollbacks.append((type_, from_level, to_level))

        datasource.call_on_head(on_head)
        datasource.call_on_rollback(on_rollback)


def _node_datasource() -> tuple[EvmNodeDatasource, Recorder]:
    # NOTE: Datasource is never started; the emitter only leaves the process to fetch a full block.
    config = EvmNodeDatasourceConfig(kind='evm.node', url='http://localhost', ws_url='ws://localhost')
    config._name = 'node'

    datasource = EvmNodeDatasource(config)
    datasource.get_block_by_level = AsyncMock(return_value={'transactions': []})  # type: ignore[method-assign]
    recorder = Recorder()
    recorder.attach(datasource)
    return datasource, recorder


async def _drain(datasource: EvmNodeDatasource) -> None:
    try:
        await asyncio.wait_for(datasource._emitter_loop(), timeout=DRAIN_TIMEOUT)
    except TimeoutError:
        pass


async def test_head_is_emitted() -> None:
    datasource, recorder = _node_datasource()

    await datasource._handle_subscription(PLAIN_HEAD, _head_json(BLOCK_HASH, 42))
    await _drain(datasource)

    assert recorder.heads == [42]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}


async def test_distinct_heads_are_emitted() -> None:
    datasource, recorder = _node_datasource()

    await datasource._handle_subscription(PLAIN_HEAD, _head_json('0x' + 'a1' * 32, 42))
    await datasource._handle_subscription(PLAIN_HEAD, _head_json('0x' + 'a2' * 32, 43))
    await _drain(datasource)

    assert recorder.heads == [42, 43]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}


async def test_head_from_two_subscriptions_is_emitted_once() -> None:
    datasource, recorder = _node_datasource()

    await datasource._handle_subscription(PLAIN_HEAD, _head_json(BLOCK_HASH, 42))
    await datasource._handle_subscription(TRANSACTIONS_HEAD, _head_json(BLOCK_HASH, 42))
    await _drain(datasource)

    # NOTE: Emitting the second announcement would re-emit the head and, since its level is not
    # greater than the known one, fire a rollback on every EVM channel — a phantom one-level reorg.
    assert recorder.heads == [42]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}
    # NOTE: Folding the pair must not lose what the second announcement asked for.
    datasource.get_block_by_level.assert_awaited_once_with(block_number=42, full_transactions=True)  # type: ignore[attr-defined]


async def test_head_announced_again_during_emit_is_ignored() -> None:
    datasource, recorder = _node_datasource()

    # NOTE: `on_head` runs inside the emitter pass, after the queue item was taken but before the
    # level data is dropped — the window a queue-membership check would miss.
    async def announce_again(_datasource: EvmNodeDatasource, _head: EvmNodeHeadData) -> None:
        await datasource._handle_subscription(TRANSACTIONS_HEAD, _head_json(BLOCK_HASH, 42))

    datasource.call_on_head(announce_again)

    await datasource._handle_subscription(PLAIN_HEAD, _head_json(BLOCK_HASH, 42))
    await _drain(datasource)

    assert recorder.heads == [42]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}
    datasource.get_block_by_level.assert_awaited_once_with(block_number=42, full_transactions=True)  # type: ignore[attr-defined]
