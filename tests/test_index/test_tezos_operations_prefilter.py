from collections.abc import Iterator
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast

import pytest

from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig as TransactionPattern
from dipdup.config.tezos_operations import TezosOperationsIndexConfig
from dipdup.config.tezos_operations import TezosOperationsUnfilteredIndexConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.dipdup import IndexDispatcher
from dipdup.indexes.tezos_operations.index import TezosOperationsIndex
from dipdup.indexes.tezos_operations.index import extract_operation_subgroups
from dipdup.models.tezos import TezosOperationData
from dipdup.performance import queues

MINE = 'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'
OTHER = 'KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9'
UNRELATED = 'KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn'
MINE_CODE_HASH = 111

DATASOURCE = cast('TezosTzktDatasource', object())


@pytest.fixture(autouse=True)
def _remove_spawned_queues() -> Iterator[None]:
    # NOTE: Queue registry is process-wide; index names repeat between tests
    known_queues = set(queues._queues)
    yield
    for name in set(queues._queues) - known_queues:
        queues.remove_queue(name)


def transaction(id_: int, target: str, target_code_hash: int | None = None) -> TezosOperationData:
    return TezosOperationData(
        type='transaction',
        id=id_,
        level=1,
        timestamp=datetime.now(UTC),
        hash=f'op{id_}',
        counter=id_,
        sender_address='tz1aKTCbAUuea2RV9kxqRVRg3HT7f1RKnp6a',
        target_address=target,
        initiator_address=None,
        amount=0,
        status='applied',
        has_internals=False,
        storage=None,
        block=None,
        sender_alias=None,
        nonce=None,
        target_alias=None,
        initiator_alias=None,
        entrypoint='transfer',
        parameter_json=None,
        originated_contract_address=None,
        originated_contract_alias=None,
        originated_contract_type_hash=None,
        originated_contract_code_hash=None,
        originated_contract_tzips=None,
        delegate_address=None,
        delegate_alias=None,
        target_code_hash=target_code_hash,
        sender_code_hash=None,
    )


def kept(operations: tuple[TezosOperationData, ...], addresses: set[str], code_hashes: set[int]) -> set[int]:
    subgroups = extract_operation_subgroups(
        operations,
        addresses=addresses,
        entrypoints=set(),
        code_hashes=code_hashes,
    )
    return {op.id for subgroup in subgroups for op in subgroup.operations}


@pytest.mark.parametrize(
    ('addresses', 'code_hashes', 'expected'),
    [
        ({MINE}, set(), {1}),
        (set(), {MINE_CODE_HASH}, {1}),
        # NOTE: guard, worked before
        ({MINE}, {MINE_CODE_HASH}, {1}),
        # NOTE: guard, no filter keeps everything
        (set(), set(), {1, 2}),
    ],
    ids=['address-only', 'code-hash-only', 'guard-both', 'guard-none'],
)
def test_prefilter_drops_transactions_matching_no_filter(
    addresses: set[str],
    code_hashes: set[int],
    expected: set[int],
) -> None:
    operations = (
        transaction(1, MINE, MINE_CODE_HASH),
        transaction(2, UNRELATED),
    )
    assert kept(operations, addresses, code_hashes) == expected


def filtered_index(name: str, *destinations: TezosContractConfig) -> TezosOperationsIndex:
    config = TezosOperationsIndexConfig(
        datasources=(TezosTzktDatasourceConfig(),),
        handlers=tuple(
            TezosOperationsHandlerConfig(
                callback=f'on_{i}',
                pattern=(TransactionPattern(destination=destination, entrypoint='transfer'),),
            )
            for i, destination in enumerate(destinations)
        ),
    )
    return make_index(name, config)


def open_index(name: str) -> TezosOperationsIndex:
    """Index with a transaction pattern that has neither `source` nor `destination`"""
    config = TezosOperationsIndexConfig(
        datasources=(TezosTzktDatasourceConfig(),),
        handlers=(
            TezosOperationsHandlerConfig(
                callback='on_mine',
                pattern=(TransactionPattern(destination=TezosContractConfig(address=MINE), entrypoint='transfer'),),
            ),
            TezosOperationsHandlerConfig(
                callback='on_any',
                pattern=(TransactionPattern(entrypoint='transfer'),),
            ),
        ),
    )
    return make_index(name, config)


def unfiltered_index(name: str) -> TezosOperationsIndex:
    config = TezosOperationsUnfilteredIndexConfig(
        datasources=(TezosTzktDatasourceConfig(),),
        callback='on_operation',
    )
    return make_index(name, config)


def make_index(name: str, config: Any) -> TezosOperationsIndex:
    config._name = name
    return TezosOperationsIndex(cast('Any', None), config, (DATASOURCE,))


async def dispatch(indexes: list[TezosOperationsIndex], operations: tuple[TezosOperationData, ...]) -> None:
    dispatcher = IndexDispatcher(cast('Any', None))
    for index in indexes:
        dispatcher._indexes[index.name] = index
        await dispatcher._apply_filters(index)
    await dispatcher._on_tzkt_operations(DATASOURCE, operations)


def received(index: TezosOperationsIndex) -> set[int]:
    return {op.id for message in index.queue for subgroup in message for op in subgroup.operations}


async def test_realtime_drops_transactions_of_no_index() -> None:
    index = filtered_index('mine', TezosContractConfig(address=MINE))
    await dispatch([index], (transaction(1, MINE), transaction(2, UNRELATED)))
    assert received(index) == {1}


@pytest.mark.parametrize('open_first', [True, False], ids=['open-first', 'open-spawned-later'])
@pytest.mark.parametrize(
    'make_open',
    [open_index, unfiltered_index],
    ids=['open-pattern', 'unfiltered'],
)
async def test_realtime_open_index_keeps_every_transaction(make_open: Any, open_first: bool) -> None:
    """guard: the prefilter was a no-op with address-only filters, it must stay open for these indexes"""
    filtered = filtered_index('mine', TezosContractConfig(address=OTHER))
    open_ = make_open('open')
    indexes = [open_, filtered] if open_first else [filtered, open_]

    await dispatch(indexes, (transaction(1, MINE), transaction(2, UNRELATED)))
    assert received(open_) == {1, 2}


@pytest.mark.parametrize('open_first', [True, False], ids=['open-first', 'open-spawned-later'])
async def test_realtime_open_index_next_to_address_and_code_hash_filters(open_first: bool) -> None:
    filtered = filtered_index(
        'mine',
        TezosContractConfig(address=OTHER),
        TezosContractConfig(code_hash=MINE_CODE_HASH),
    )
    open_ = open_index('open')
    indexes = [open_, filtered] if open_first else [filtered, open_]

    await dispatch(indexes, (transaction(1, MINE), transaction(2, UNRELATED)))
    assert received(open_) == {1, 2}
