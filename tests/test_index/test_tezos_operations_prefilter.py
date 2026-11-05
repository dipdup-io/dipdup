from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast

from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig as TransactionPattern
from dipdup.config.tezos_operations import TezosOperationsIndexConfig
from dipdup.config.tezos_operations import TezosOperationsUnfilteredIndexConfig
from dipdup.dipdup import IndexDispatcher
from dipdup.indexes.tezos_operations.index import TezosOperationsIndex
from dipdup.indexes.tezos_operations.index import extract_operation_subgroups
from dipdup.indexes.tezos_operations.index import has_open_transaction_pattern
from dipdup.models.tezos import TezosOperationData

MINE = 'KT1MINE'
OTHER = 'KT1OTHER'
CODE_MINE = 111
CODE_OTHER = 222


def transaction(
    target: str,
    sender: str = 'tz1sender',
    target_code_hash: int | None = None,
    sender_code_hash: int | None = None,
) -> TezosOperationData:
    return TezosOperationData(
        type='transaction',
        id=1,
        level=1,
        timestamp=datetime.now(UTC),
        hash=f'op-{target}-{target_code_hash}',
        counter=1,
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
        entrypoint='default',
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


def kept_targets(
    operations: list[TezosOperationData],
    addresses: set[str],
    code_hashes: set[int],
) -> list[str | None]:
    subgroups = extract_operation_subgroups(
        operations,
        addresses=addresses,
        entrypoints=set(),
        code_hashes=code_hashes,
    )
    return [group.operations[0].target_address for group in subgroups]


def test_prefilter_drops_with_only_address_filter() -> None:
    operations = [transaction(MINE, target_code_hash=CODE_MINE), transaction(OTHER, target_code_hash=CODE_OTHER)]
    assert kept_targets(operations, {MINE}, set()) == [MINE]


def test_prefilter_drops_with_only_code_hash_filter() -> None:
    operations = [transaction(MINE, target_code_hash=CODE_MINE), transaction(OTHER, target_code_hash=CODE_OTHER)]
    assert kept_targets(operations, set(), {CODE_MINE}) == [MINE]


def test_prefilter_drops_with_both_filters_set() -> None:
    operations = [transaction(MINE, target_code_hash=CODE_MINE), transaction(OTHER, target_code_hash=CODE_OTHER)]
    assert kept_targets(operations, {MINE}, {CODE_MINE}) == [MINE]


def test_prefilter_keeps_everything_without_filters() -> None:
    operations = [transaction(MINE, target_code_hash=CODE_MINE), transaction(OTHER, target_code_hash=CODE_OTHER)]
    assert kept_targets(operations, set(), set()) == [MINE, OTHER]


def test_prefilter_keeps_operation_matching_either_filter() -> None:
    # NOTE: Matching either non-empty set is enough to survive the prefilter;
    # the matcher still decides whether a handler actually runs.
    address_only = transaction(MINE, target_code_hash=CODE_OTHER)
    code_only = transaction(OTHER, target_code_hash=CODE_MINE)
    neither = transaction(OTHER, target_code_hash=CODE_OTHER)
    assert kept_targets([address_only, code_only, neither], {MINE}, {CODE_MINE}) == [MINE, OTHER]


# NOTE: Contract addresses are validated, so use a real one here; the
# operation fixtures above use plain strings and are unaffected.
MINE_CONTRACT = 'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'


def contract(address: str | None = None, code_hash: int | None = None) -> TezosContractConfig:
    return TezosContractConfig(kind='tezos', address=address, code_hash=code_hash)  # type: ignore[arg-type]


def test_has_open_transaction_pattern() -> None:
    open_handlers = (
        TezosOperationsHandlerConfig(callback='on_any', pattern=(TransactionPattern(entrypoint='default'),)),
    )
    assert has_open_transaction_pattern(open_handlers)

    filtered_handlers = (
        TezosOperationsHandlerConfig(
            callback='on_mine',
            pattern=(TransactionPattern(entrypoint='default', destination=contract(address=MINE_CONTRACT)),),
        ),
    )
    assert not has_open_transaction_pattern(filtered_handlers)

    code_hash_handlers = (
        TezosOperationsHandlerConfig(
            callback='on_code',
            pattern=(TransactionPattern(entrypoint='default', source=contract(code_hash=CODE_MINE)),),
        ),
    )
    assert not has_open_transaction_pattern(code_hash_handlers)


def make_index(handlers: tuple[TezosOperationsHandlerConfig, ...]) -> TezosOperationsIndex:
    config = TezosOperationsIndexConfig(datasources=(), handlers=handlers)
    config._name = 'test'
    return TezosOperationsIndex(cast('Any', None), config, ())


async def test_get_filters_stays_open_with_open_pattern() -> None:
    index = make_index(
        (
            TezosOperationsHandlerConfig(
                callback='on_mine',
                pattern=(TransactionPattern(entrypoint='default', destination=contract(address=MINE_CONTRACT)),),
            ),
            TezosOperationsHandlerConfig(
                callback='on_any',
                pattern=(TransactionPattern(entrypoint='default'),),
            ),
        )
    )
    _, addresses, code_hashes = await index.get_filters()
    assert addresses == set()
    assert code_hashes == set()


async def test_get_filters_narrows_without_open_pattern() -> None:
    index = make_index(
        (
            TezosOperationsHandlerConfig(
                callback='on_mine',
                pattern=(TransactionPattern(entrypoint='default', destination=contract(address=MINE_CONTRACT)),),
            ),
        )
    )
    _, addresses, code_hashes = await index.get_filters()
    assert addresses == {MINE_CONTRACT}
    assert code_hashes == set()


async def test_realtime_union_filter_stays_open() -> None:
    dispatcher = IndexDispatcher(cast('Any', None))
    filtered = make_index(
        (
            TezosOperationsHandlerConfig(
                callback='on_mine',
                pattern=(TransactionPattern(entrypoint='default', destination=contract(address=MINE_CONTRACT)),),
            ),
        )
    )
    open_index = make_index(
        (
            TezosOperationsHandlerConfig(
                callback='on_any',
                pattern=(TransactionPattern(entrypoint='default'),),
            ),
        )
    )
    await dispatcher._apply_filters(filtered)
    assert dispatcher._address_filter == {MINE_CONTRACT}
    await dispatcher._apply_filters(open_index)
    assert dispatcher._address_filter == set()
    assert dispatcher._code_hash_filter == set()
    # NOTE: A filtered index applied after an open one must not narrow it again.
    await dispatcher._apply_filters(filtered)
    assert dispatcher._address_filter == set()


async def test_realtime_union_filter_stays_open_for_unfiltered_index() -> None:
    dispatcher = IndexDispatcher(cast('Any', None))
    filtered = make_index(
        (
            TezosOperationsHandlerConfig(
                callback='on_mine',
                pattern=(TransactionPattern(entrypoint='default', destination=contract(address=MINE_CONTRACT)),),
            ),
        )
    )
    unfiltered_config = TezosOperationsUnfilteredIndexConfig(datasources=(), callback='on_all')
    unfiltered_config._name = 'test'
    unfiltered = TezosOperationsIndex(cast('Any', None), unfiltered_config, ())
    await dispatcher._apply_filters(filtered)
    await dispatcher._apply_filters(unfiltered)
    assert dispatcher._address_filter == set()
    assert dispatcher._code_hash_filter == set()
