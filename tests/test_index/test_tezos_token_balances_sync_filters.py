from collections import Counter
from collections.abc import AsyncIterator
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_token_balances import TezosTokenBalancesHandlerConfig
from dipdup.config.tezos_token_balances import TezosTokenBalancesIndexConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.indexes.tezos_token_balances.index import TezosTokenBalancesIndex
from dipdup.indexes.tezos_token_balances.matcher import match_token_balances
from dipdup.models.tezos import TezosTokenBalanceData
from dipdup.performance import queues

TOKEN = 'KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn'
OTHER_TOKEN = 'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'


@pytest.fixture(autouse=True)
def _remove_spawned_queues() -> Iterator[None]:
    # NOTE: Queue registry is process-wide; index names repeat between tests
    known_queues = set(queues._queues)
    yield
    for name in set(queues._queues) - known_queues:
        queues.remove_queue(name)


def balance(id_: int, contract: str, token_id: int) -> TezosTokenBalanceData:
    return TezosTokenBalanceData(
        id=id_,
        transfers_count=1,
        first_level=1,
        first_time=datetime.now(UTC),
        last_level=1,
        last_time=datetime.now(UTC),
        account_address='tz1aKTCbAUuea2RV9kxqRVRg3HT7f1RKnp6a',
        account_alias=None,
        tzkt_token_id=id_ * 1000,
        contract_address=contract,
        contract_alias=None,
        token_id=token_id,
        standard=None,
        metadata=None,
        balance='1',
        balance_value=None,
    )


BALANCES = (
    balance(1, TOKEN, 0),
    balance(2, TOKEN, 1),
    balance(3, OTHER_TOKEN, 0),
    balance(4, OTHER_TOKEN, 1),
    balance(5, OTHER_TOKEN, 2),
)


class FakeTzkt:
    """Answers like TzKT: an empty filter matches everything, non-empty filters are combined with AND"""

    def __init__(self) -> None:
        self.filters: dict[str, set[Any]] = {}

    async def iter_token_balances(
        self,
        token_addresses: set[str],
        token_ids: set[int],
        first_level: int | None = None,
        last_level: int | None = None,
    ) -> AsyncIterator[tuple[TezosTokenBalanceData, ...]]:
        self.filters = {'token_addresses': token_addresses, 'token_ids': token_ids}
        yield tuple(
            b
            for b in BALANCES
            if (not token_addresses or b.contract_address in token_addresses)
            and (not token_ids or b.token_id in token_ids)
        )


def handler(callback: str, contract: str | None = None, token_id: int | None = None) -> TezosTokenBalancesHandlerConfig:
    return TezosTokenBalancesHandlerConfig(
        callback=callback,
        contract=TezosContractConfig(kind='tezos', address=contract) if contract else None,
        token_id=token_id,
    )


async def sync_calls(datasource: FakeTzkt, *handlers: TezosTokenBalancesHandlerConfig) -> Counter[str]:
    """Callbacks called by sync"""
    config = TezosTokenBalancesIndexConfig(datasources=(TezosTzktDatasourceConfig(),), handlers=handlers)
    config._name = 'balances'
    for handler_config in handlers:
        handler_config.parent = config

    @asynccontextmanager
    async def in_transaction(*args: Any, **kwargs: Any) -> AsyncIterator[None]:
        yield

    ctx = MagicMock()
    ctx.transactions.in_transaction = in_transaction
    ctx.fire_handler = AsyncMock()
    index = TezosTokenBalancesIndex(ctx, config, (cast('TezosTzktDatasource', datasource),))
    index._update_state = AsyncMock()  # type: ignore[method-assign]

    await index._synchronize_actual(10)

    return Counter(call.kwargs['name'] for call in ctx.fire_handler.call_args_list)


def all_matches(*handlers: TezosTokenBalancesHandlerConfig) -> Counter[str]:
    return Counter(handler_config.callback for handler_config, _ in match_token_balances(handlers, BALANCES))


async def test_sync_delivers_balances_to_handlers_with_different_filters() -> None:
    handlers = (
        handler('on_token_0', contract=TOKEN, token_id=0),
        handler('on_other', contract=OTHER_TOKEN),
    )
    datasource = FakeTzkt()

    calls = await sync_calls(datasource, *handlers)

    assert datasource.filters == {'token_addresses': {TOKEN, OTHER_TOKEN}, 'token_ids': set()}
    assert calls == all_matches(*handlers) == Counter(on_token_0=1, on_other=3)


@pytest.mark.parametrize(
    'handlers',
    [
        (handler('on_token_1', token_id=1), handler('on_token', contract=TOKEN)),
        (handler('on_token', contract=TOKEN), handler('on_any')),
        (handler('on_token_2', token_id=2), handler('on_any')),
    ],
    ids=['disjoint-fields', 'unfiltered-contract', 'unfiltered-token-id'],
)
async def test_sync_fetches_everything_handlers_match(handlers: tuple[TezosTokenBalancesHandlerConfig, ...]) -> None:
    calls = await sync_calls(FakeTzkt(), *handlers)

    assert calls == all_matches(*handlers)


async def test_sync_filters_by_fields_set_in_every_handler() -> None:
    # NOTE: guard, a field every handler sets still narrows the request
    handlers = (
        handler('on_token_0', contract=TOKEN, token_id=0),
        handler('on_other_2', contract=OTHER_TOKEN, token_id=2),
    )
    datasource = FakeTzkt()

    calls = await sync_calls(datasource, *handlers)

    assert datasource.filters == {'token_addresses': {TOKEN, OTHER_TOKEN}, 'token_ids': {0, 2}}
    assert calls == all_matches(*handlers)


@pytest.mark.parametrize(
    ('token_addresses', 'token_ids', 'expected'),
    [
        # NOTE: `token.id` is TzKT internal ID of the token, not the one handlers filter by
        ({TOKEN}, {152}, {'token.contract.in': TOKEN, 'token.tokenId.in': '152'}),
        ({TOKEN}, set(), {'token.contract.in': TOKEN}),
        (set(), set(), {}),
    ],
    ids=['token-id-of-contract', 'no-token-id', 'no-filters'],
)
async def test_request_filters(token_addresses: set[str], token_ids: set[int], expected: dict[str, str]) -> None:
    config = TezosTzktDatasourceConfig()
    config._name = 'tzkt'
    datasource = TezosTzktDatasource(config)
    request = AsyncMock(return_value=())
    datasource._request_values_dict = request  # type: ignore[method-assign]

    await datasource.get_token_balances(token_addresses, token_ids, last_level=10)

    params = request.call_args.kwargs['params']
    assert {k: v for k, v in params.items() if k.endswith('.in')} == expected
