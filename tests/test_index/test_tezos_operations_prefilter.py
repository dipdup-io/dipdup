from collections.abc import Iterator
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast

import pytest

from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerOriginationPatternConfig as OriginationPattern
from dipdup.config.tezos_operations import (
    TezosOperationsHandlerSmartRollupExecutePatternConfig as SmartRollupExecutePattern,
)
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig as TransactionPattern
from dipdup.config.tezos_operations import TezosOperationsIndexConfig
from dipdup.config.tezos_operations import TezosOperationsUnfilteredIndexConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.dipdup import IndexDispatcher
from dipdup.indexes.tezos_operations.index import TezosOperationsIndex
from dipdup.indexes.tezos_operations.index import extract_operation_subgroups
from dipdup.models.tezos import TezosOperationData
from dipdup.models.tezos import TezosOperationType
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


def transaction(
    id_: int,
    target: str,
    target_code_hash: int | None = None,
    sender: str = 'tz1aKTCbAUuea2RV9kxqRVRg3HT7f1RKnp6a',
    sender_code_hash: int | None = None,
    entrypoint: str | None = 'transfer',
) -> TezosOperationData:
    return TezosOperationData(
        type='transaction',
        id=id_,
        level=1,
        timestamp=datetime.now(UTC),
        hash=f'op{id_}',
        counter=id_,
        sender_address=sender,
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
        entrypoint=entrypoint,
        parameter_json=None,
        originated_contract_address=None,
        originated_contract_alias=None,
        originated_contract_type_hash=None,
        originated_contract_code_hash=None,
        originated_contract_tzips=None,
        delegate_address=None,
        delegate_alias=None,
        target_code_hash=target_code_hash,
        sender_code_hash=sender_code_hash,
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


def source_index(name: str, source: TezosContractConfig) -> TezosOperationsIndex:
    """Index with a transaction pattern that has only `source`, like a deposits index watching one sender"""
    config = TezosOperationsIndexConfig(
        datasources=(TezosTzktDatasourceConfig(),),
        handlers=(TezosOperationsHandlerConfig(callback='on_sent', pattern=(TransactionPattern(source=source),)),),
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


@pytest.mark.parametrize(
    ('make_index_', 'every_transaction'),
    [
        (lambda: open_index('open'), True),
        (lambda: unfiltered_index('open'), True),
        (lambda: filtered_index('mine', TezosContractConfig(address=MINE)), False),
        (lambda: source_index('sent', TezosContractConfig(address=MINE)), False),
    ],
    ids=['open-pattern', 'unfiltered', 'filtered', 'source-only'],
)
async def test_index_tells_whether_it_needs_every_transaction(make_index_: Any, every_transaction: bool) -> None:
    index = make_index_()
    # NOTE: guard, callers outside the framework unpack exactly three filters
    _, _, _ = await index.get_filters()
    assert index.needs_every_transaction is every_transaction


@pytest.mark.parametrize(
    ('source', 'sent'),
    [
        (TezosContractConfig(address=MINE), transaction(1, UNRELATED, sender=MINE, entrypoint=None)),
        (
            TezosContractConfig(code_hash=MINE_CODE_HASH),
            transaction(1, UNRELATED, sender_code_hash=MINE_CODE_HASH, entrypoint=None),
        ),
    ],
    ids=['source-address', 'source-code-hash'],
)
async def test_realtime_source_only_pattern_keeps_prefilter(
    source: TezosContractConfig, sent: TezosOperationData
) -> None:
    index = source_index('sent', source)
    await dispatch([index], (sent, transaction(2, UNRELATED, entrypoint=None)))
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


def no_transactions_index(name: str, pattern: Any) -> TezosOperationsIndex:
    config = TezosOperationsIndexConfig(
        datasources=(TezosTzktDatasourceConfig(),),
        types=(TezosOperationType.origination, TezosOperationType.sr_execute),
        handlers=(TezosOperationsHandlerConfig(callback='on_other', pattern=(pattern,)),),
    )
    return make_index(name, config)


@pytest.mark.parametrize(
    'pattern',
    [
        OriginationPattern(source=TezosContractConfig(address=OTHER)),
        SmartRollupExecutePattern(source=TezosContractConfig(address=OTHER)),
    ],
    ids=['origination-by-source', 'sr-execute-by-source'],
)
async def test_realtime_index_without_transaction_patterns_keeps_prefilter(pattern: Any) -> None:
    """guard: the prefilter worked with both filters set before, an index that needs no transactions must not open it"""
    filtered = filtered_index(
        'mine',
        TezosContractConfig(address=OTHER),
        TezosContractConfig(code_hash=MINE_CODE_HASH),
    )
    other = no_transactions_index('other', pattern)

    await dispatch([filtered, other], (transaction(1, OTHER), transaction(2, UNRELATED)))
    assert received(filtered) == {1}


async def test_realtime_code_hash_pattern_keeps_prefilter() -> None:
    index = filtered_index('mine', TezosContractConfig(code_hash=MINE_CODE_HASH))

    await dispatch([index], (transaction(1, MINE, MINE_CODE_HASH), transaction(2, UNRELATED)))
    assert received(index) == {1}


async def synchronize(
    index: TezosOperationsIndex,
    operations: tuple[TezosOperationData, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> set[int]:
    """Ids of operations that reach matching when the level is fetched during sync"""
    await dispatch([index], ())

    class Fetcher:
        async def fetch_by_level(self) -> Any:
            yield 1, operations

    processed: set[int] = set()

    async def process_level_data(subgroups: Any, sync_level: int) -> None:
        processed.update(op.id for subgroup in subgroups for op in subgroup.operations)

    async def noop(*args: Any) -> Any:
        return 0

    async def create_fetcher(*args: Any) -> Fetcher:
        return Fetcher()

    monkeypatch.setattr(index, '_enter_sync_state', noop)
    monkeypatch.setattr(index, '_exit_sync_state', noop)
    monkeypatch.setattr(index, '_create_fetcher', create_fetcher)
    monkeypatch.setattr(index, '_process_level_data', process_level_data)

    await index._synchronize(1)
    return processed


@pytest.mark.parametrize(
    ('make_index_', 'expected'),
    [
        (lambda: open_index('open'), {1, 2}),
        # NOTE: guard, own filters of a filtered index still apply
        (lambda: filtered_index('mine', TezosContractConfig(address=MINE)), {1}),
    ],
    ids=['open-pattern', 'guard-filtered'],
)
async def test_sync_open_index_keeps_every_transaction(
    make_index_: Any,
    expected: set[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operations = (transaction(1, MINE), transaction(2, UNRELATED))
    assert await synchronize(make_index_(), operations, monkeypatch) == expected


def any_entrypoint_index(name: str) -> TezosOperationsIndex:
    """Index with a transaction pattern item that has no `entrypoint`, next to an item that names one"""
    mine = TezosContractConfig(address=MINE)
    config = TezosOperationsIndexConfig(
        datasources=(TezosTzktDatasourceConfig(),),
        handlers=(
            TezosOperationsHandlerConfig(callback='on_call', pattern=(TransactionPattern(destination=mine),)),
            TezosOperationsHandlerConfig(
                callback='on_mint',
                pattern=(TransactionPattern(destination=mine, entrypoint='mint'),),
            ),
        ),
    )
    return make_index(name, config)


# NOTE: A plain tez transfer has no entrypoint
CALLS_TO_MINE = (
    transaction(1, MINE, entrypoint='transfer'),
    transaction(2, MINE, entrypoint='mint'),
    transaction(3, MINE, entrypoint=None),
    transaction(4, MINE, entrypoint='burn'),
)


@pytest.mark.parametrize(
    ('make_index_', 'every_entrypoint'),
    [
        (lambda: any_entrypoint_index('any'), True),
        (lambda: unfiltered_index('any'), True),
        (lambda: filtered_index('mine', TezosContractConfig(address=MINE)), False),
        (lambda: no_transactions_index('other', OriginationPattern(source=TezosContractConfig(address=OTHER))), False),
    ],
    ids=['no-entrypoint', 'unfiltered', 'filtered', 'no-transactions'],
)
async def test_index_tells_whether_it_needs_every_entrypoint(make_index_: Any, every_entrypoint: bool) -> None:
    index = make_index_()
    # NOTE: guard, callers outside the framework unpack exactly three filters
    _, _, _ = await index.get_filters()
    assert index.needs_every_entrypoint is every_entrypoint


@pytest.mark.parametrize(
    ('make_index_', 'expected'),
    [
        (lambda: any_entrypoint_index('any'), {1, 2, 3, 4}),
        # NOTE: guard, an index that names every entrypoint still gets only those
        (lambda: filtered_index('mine', TezosContractConfig(address=MINE)), {1}),
    ],
    ids=['no-entrypoint', 'guard-filtered'],
)
async def test_sync_item_without_entrypoint_keeps_every_entrypoint(
    make_index_: Any,
    expected: set[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert await synchronize(make_index_(), CALLS_TO_MINE, monkeypatch) == expected


@pytest.mark.parametrize('any_first', [True, False], ids=['any-first', 'any-spawned-later'])
@pytest.mark.parametrize(
    'make_any',
    [any_entrypoint_index, unfiltered_index],
    ids=['no-entrypoint', 'unfiltered'],
)
async def test_realtime_any_entrypoint_index_keeps_every_entrypoint(make_any: Any, any_first: bool) -> None:
    filtered = filtered_index('other', TezosContractConfig(address=OTHER))
    any_ = make_any('any')
    indexes = [any_, filtered] if any_first else [filtered, any_]

    await dispatch(indexes, CALLS_TO_MINE)
    assert received(any_) == {1, 2, 3, 4}


async def test_realtime_index_without_transaction_patterns_keeps_entrypoint_prefilter() -> None:
    """guard: an index that needs no transactions returns empty filters too, it must not open the prefilter"""
    filtered = filtered_index('mine', TezosContractConfig(address=MINE))
    other = no_transactions_index('other', OriginationPattern(source=TezosContractConfig(address=OTHER)))

    await dispatch([filtered, other], CALLS_TO_MINE)
    assert received(filtered) == {1}
