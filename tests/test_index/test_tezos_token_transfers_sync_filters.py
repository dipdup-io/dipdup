from collections import Counter
from collections.abc import AsyncIterator
from collections.abc import Iterator
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast
from unittest.mock import AsyncMock

import pytest

from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_token_transfers import TezosTokenTransfersHandlerConfig
from dipdup.config.tezos_token_transfers import TezosTokenTransfersIndexConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.indexes.tezos_token_transfers.index import TezosTokenTransfersIndex
from dipdup.indexes.tezos_token_transfers.matcher import match_token_transfers
from dipdup.models.tezos import TezosTokenTransferData
from dipdup.performance import queues

TOKEN = 'KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn'
OTHER_TOKEN = 'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'
ALICE = 'tz1aKTCbAUuea2RV9kxqRVRg3HT7f1RKnp6a'
BOB = 'tz1VSUr8wwNhLAzempoch5d6hLRiTh8Cjcjb'
CAROL = 'tz1burnburnburnburnburnburnburjAYjjX'


@pytest.fixture(autouse=True)
def _remove_spawned_queues() -> Iterator[None]:
    # NOTE: Queue registry is process-wide; index names repeat between tests
    known_queues = set(queues._queues)
    yield
    for name in set(queues._queues) - known_queues:
        queues.remove_queue(name)


def transfer(id_: int, contract: str, from_: str, to: str, token_id: int = 0) -> TezosTokenTransferData:
    return TezosTokenTransferData(
        id=id_,
        level=id_,
        timestamp=datetime.now(UTC),
        tzkt_token_id=1,
        contract_address=contract,
        contract_alias=None,
        token_id=token_id,
        standard=None,
        metadata=None,
        from_alias=None,
        from_address=from_,
        to_alias=None,
        to_address=to,
        amount=1,
        tzkt_transaction_id=None,
        tzkt_origination_id=None,
        tzkt_migration_id=None,
    )


TRANSFERS = (
    transfer(1, TOKEN, ALICE, CAROL),
    transfer(2, TOKEN, CAROL, BOB),
    transfer(3, TOKEN, ALICE, BOB),
    transfer(4, TOKEN, CAROL, CAROL),
    transfer(5, OTHER_TOKEN, ALICE, BOB),
    transfer(6, TOKEN, ALICE, CAROL, token_id=1),
)


class FakeTzkt:
    """Answers like TzKT: an empty filter matches everything, non-empty filters are combined with AND"""

    def __init__(self) -> None:
        self.filters: dict[str, set[Any]] = {}

    async def iter_token_transfers(
        self,
        token_addresses: set[str],
        token_ids: set[int],
        from_addresses: set[str],
        to_addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[TezosTokenTransferData, ...]]:
        self.filters = {
            'token_addresses': token_addresses,
            'token_ids': token_ids,
            'from_addresses': from_addresses,
            'to_addresses': to_addresses,
        }
        yield tuple(
            t
            for t in TRANSFERS
            if (not token_addresses or t.contract_address in token_addresses)
            and (not token_ids or t.token_id in token_ids)
            and (not from_addresses or t.from_address in from_addresses)
            and (not to_addresses or t.to_address in to_addresses)
        )


def handler(callback: str, **filters: Any) -> TezosTokenTransfersHandlerConfig:
    token_id = filters.pop('token_id', None)
    contracts = {k: TezosContractConfig(kind='tezos', address=v) for k, v in filters.items()}
    return TezosTokenTransfersHandlerConfig(callback=callback, token_id=token_id, **contracts)


def make_index(datasource: FakeTzkt, *handlers: TezosTokenTransfersHandlerConfig) -> TezosTokenTransfersIndex:
    config = TezosTokenTransfersIndexConfig(datasources=(TezosTzktDatasourceConfig(),), handlers=handlers)
    config._name = 'transfers'
    return TezosTokenTransfersIndex(cast('Any', None), config, (cast('TezosTzktDatasource', datasource),))


async def sync_matches(index: TezosTokenTransfersIndex) -> Counter[str]:
    """Callbacks called for the transfers that sync fetches"""
    matches: Counter[str] = Counter()
    async for _, batch in index._create_fetcher(1, 10).fetch_by_level():
        matches.update(
            handler_config.callback for handler_config, _ in index._match_level_data(index._config.handlers, batch)
        )
    return matches


def all_matches(*handlers: TezosTokenTransfersHandlerConfig) -> Counter[str]:
    return Counter(handler_config.callback for handler_config, _ in match_token_transfers(handlers, TRANSFERS))


async def test_sync_delivers_transfers_to_handlers_with_different_filters() -> None:
    handlers = (
        handler('on_from_alice', contract=TOKEN, from_=ALICE),
        handler('on_to_bob', contract=TOKEN, to=BOB),
    )
    datasource = FakeTzkt()

    matches = await sync_matches(make_index(datasource, *handlers))

    assert datasource.filters == {
        'token_addresses': {TOKEN},
        'token_ids': set(),
        'from_addresses': set(),
        'to_addresses': set(),
    }
    assert matches == all_matches(*handlers) == Counter(on_from_alice=3, on_to_bob=2)


@pytest.mark.parametrize(
    'handlers',
    [
        (handler('on_token', contract=TOKEN), handler('on_other_from_alice', contract=OTHER_TOKEN, from_=ALICE)),
        (handler('on_token_0', contract=TOKEN, token_id=0), handler('on_token_any', contract=TOKEN)),
        (handler('on_to_bob', to=BOB), handler('on_any')),
        (handler('on_from_alice', from_=ALICE), handler('on_token', contract=TOKEN)),
    ],
    ids=['from-in-one', 'token-id-in-one', 'unfiltered-neighbour', 'disjoint-fields'],
)
async def test_sync_fetches_everything_handlers_match(handlers: tuple[TezosTokenTransfersHandlerConfig, ...]) -> None:
    matches = await sync_matches(make_index(FakeTzkt(), *handlers))

    assert matches == all_matches(*handlers)


async def test_sync_filters_by_fields_set_in_every_handler() -> None:
    # NOTE: guard, a field every handler sets still narrows the request
    handlers = (
        handler('on_alice_to_bob', contract=TOKEN, token_id=0, from_=ALICE, to=BOB),
        handler('on_carol_to_bob', contract=OTHER_TOKEN, token_id=1, from_=CAROL, to=BOB),
    )
    datasource = FakeTzkt()

    matches = await sync_matches(make_index(datasource, *handlers))

    assert datasource.filters == {
        'token_addresses': {TOKEN, OTHER_TOKEN},
        'token_ids': {0, 1},
        'from_addresses': {ALICE, CAROL},
        'to_addresses': {BOB},
    }
    assert matches == all_matches(*handlers)


async def test_request_omits_empty_filters() -> None:
    config = TezosTzktDatasourceConfig()
    config._name = 'tzkt'
    datasource = TezosTzktDatasource(config)
    request = AsyncMock(return_value=())
    datasource._request_values_dict = request  # type: ignore[method-assign]

    await datasource.get_token_transfers({TOKEN}, set(), set(), set(), 1, 10)

    params = request.call_args.kwargs['params']
    filters = {k: v for k, v in params.items() if k.endswith('.in')}
    assert filters == {'token.contract.in': TOKEN}


async def test_request_filters_by_token_id_of_contract() -> None:
    config = TezosTzktDatasourceConfig()
    config._name = 'tzkt'
    datasource = TezosTzktDatasource(config)
    request = AsyncMock(return_value=())
    datasource._request_values_dict = request  # type: ignore[method-assign]

    await datasource.get_token_transfers({TOKEN}, {152}, set(), set(), 1, 10)

    params = request.call_args.kwargs['params']
    filters = {k: v for k, v in params.items() if k.endswith('.in')}
    # NOTE: `token.id` is TzKT internal ID of the token, not the one handlers filter by
    assert filters == {'token.contract.in': TOKEN, 'token.tokenId.in': '152'}
