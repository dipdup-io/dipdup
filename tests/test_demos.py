from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import AsyncExitStack
from decimal import Decimal
from functools import partial

import pytest

from dipdup.database import tortoise_wrapper
from dipdup.models.tezos_tzkt import TzktOperationType
from dipdup.test import run_in_tmp
from dipdup.test import tmp_project
from tests import TEST_CONFIGS


async def assert_run_token() -> None:
    import demo_token.models

    holders = await demo_token.models.Holder.filter().count()
    holder = await demo_token.models.Holder.first()
    assert holder
    random_balance = holder.balance

    assert holders == 4
    assert random_balance == Decimal('-0.01912431')


async def assert_run_nft_marketplace() -> None:
    import demo_nft_marketplace.models

    holders = await demo_nft_marketplace.models.Holder.filter().count()
    tokens = await demo_nft_marketplace.models.Token.filter().count()
    swaps = await demo_nft_marketplace.models.Swap.filter().count()
    trades = await demo_nft_marketplace.models.Trade.filter().count()

    assert holders == 22
    assert tokens == 29
    assert swaps == 20
    assert trades == 24


async def assert_run_auction() -> None:
    import demo_auction.models

    users = await demo_auction.models.User.filter().count()
    tokens = await demo_auction.models.Token.filter().count()
    auctions = await demo_auction.models.Auction.filter().count()
    bids = await demo_auction.models.Bid.filter().count()

    assert users == 9
    assert tokens == 14
    assert auctions == 14
    assert bids == 44


async def assert_run_token_transfers(expected_holders: int, expected_balance: str) -> None:
    import demo_token_transfers.models

    holders = await demo_token_transfers.models.Holder.filter().count()
    holder = await demo_token_transfers.models.Holder.first()
    assert holder
    random_balance = holder.balance

    assert holders == expected_holders
    assert f'{random_balance:f}' == expected_balance


async def assert_run_balances() -> None:
    import demo_token_balances.models

    holders = await demo_token_balances.models.Holder.filter().count()
    holder = await demo_token_balances.models.Holder.first()
    assert holder
    random_balance = holder.balance

    assert holders == 1
    assert random_balance == 0


async def assert_run_big_maps() -> None:
    import demo_big_maps.models

    tlds = await demo_big_maps.models.TLD.filter().count()
    domains = await demo_big_maps.models.Domain.filter().count()

    assert tlds == 1
    assert domains == 1


async def assert_init(package: str) -> None:
    pass


async def assert_run_dex() -> None:
    import demo_dex.models
    from tortoise.transactions import in_transaction

    trades = await demo_dex.models.Trade.filter().count()
    positions = await demo_dex.models.Position.filter().count()
    async with in_transaction() as conn:
        symbols = (await conn.execute_query('select count(distinct(symbol)) from trade group by symbol;'))[0]
    assert symbols == 2
    assert trades == 56
    assert positions == 133


async def assert_run_domains() -> None:
    import demo_domains.models

    tlds = await demo_domains.models.TLD.filter().count()
    domains = await demo_domains.models.Domain.filter().count()

    assert tlds == 1
    assert domains == 1


async def assert_run_events() -> None:
    pass


async def assert_run_factories() -> None:
    import demo_factories.models

    from dipdup import models

    indexes = await models.Index.filter().count()
    transfers = await demo_factories.models.Transfer.filter().count()

    assert indexes == 2
    assert transfers == 1


async def assert_run_raw() -> None:
    import demo_raw.models

    transactions = await demo_raw.models.Operation.filter(type=TzktOperationType.transaction).count()
    originations = await demo_raw.models.Operation.filter(type=TzktOperationType.origination).count()
    migrations = await demo_raw.models.Operation.filter(type=TzktOperationType.migration).count()

    assert transactions == 167
    assert originations == 1
    assert migrations == 2


async def assert_run_evm_events() -> None:
    import demo_evm_events.models

    holders = await demo_evm_events.models.Holder.filter().count()
    assert holders == 26


async def assert_run_dao() -> None:
    import demo_dao.models

    proposals = await demo_dao.models.DAO.filter().count()
    votes = await demo_dao.models.Proposal.filter().count()

    assert proposals == 1
    assert votes == 1


test_args = ('config', 'package', 'cmd', 'assert_fn')
test_params = (
    ('demo_token.yml', 'demo_token', 'run', assert_run_token),
    ('demo_token.yml', 'demo_token', 'init', None),
    ('demo_nft_marketplace.yml', 'demo_nft_marketplace', 'run', assert_run_nft_marketplace),
    ('demo_nft_marketplace.yml', 'demo_nft_marketplace', 'init', None),
    ('demo_auction.yml', 'demo_auction', 'run', assert_run_auction),
    ('demo_auction.yml', 'demo_auction', 'init', None),
    ('demo_token_transfers.yml', 'demo_token_transfers', 'run', partial(assert_run_token_transfers, 4, '-0.01912431')),
    # FIXME: Why so many token transfer tests?
    ('demo_token_transfers.yml', 'demo_token_transfers', 'init', None),
    (
        'demo_token_transfers_2.yml',
        'demo_token_transfers',
        'run',
        partial(assert_run_token_transfers, 12, '0.26554711'),
    ),
    ('demo_token_transfers_3.yml', 'demo_token_transfers', 'run', partial(assert_run_token_transfers, 9, '0.15579888')),
    (
        'demo_token_transfers_4.yml',
        'demo_token_transfers',
        'run',
        partial(assert_run_token_transfers, 2, '-0.02302128'),
    ),
    ('demo_token_balances.yml', 'demo_token_balances', 'run', assert_run_balances),
    ('demo_token_balances.yml', 'demo_token_balances', 'init', None),
    ('demo_big_maps.yml', 'demo_big_maps', 'run', assert_run_big_maps),
    ('demo_big_maps.yml', 'demo_big_maps', 'init', None),
    ('demo_domains.yml', 'demo_domains', 'run', assert_run_domains),
    ('demo_domains.yml', 'demo_domains', 'init', None),
    ('demo_dex.yml', 'demo_dex', 'run', assert_run_dex),
    ('demo_dex.yml', 'demo_dex', 'init', None),
    ('demo_dao.yml', 'demo_dao', 'run', assert_run_dao),
    ('demo_dao.yml', 'demo_dao', 'init', None),
    ('demo_factories.yml', 'demo_factories', 'run', assert_run_factories),
    ('demo_factories.yml', 'demo_factories', 'init', None),
    ('demo_events.yml', 'demo_events', 'run', assert_run_events),
    ('demo_events.yml', 'demo_events', 'init', None),
    ('demo_raw.yml', 'demo_raw', 'run', assert_run_raw),
    ('demo_raw.yml', 'demo_raw', 'init', None),
    ('demo_evm_events.yml', 'demo_evm_events', 'run', assert_run_evm_events),
    ('demo_evm_events.yml', 'demo_evm_events', 'init', None),
    ('demo_evm_events_node.yml', 'demo_evm_events', 'run', assert_run_evm_events),
    ('demo_etherlink.yml', 'demo_etherlink', 'run', None),
    ('demo_etherlink.yml', 'demo_etherlink', 'init', None),
    # NOTE: Smoke tests for small tools.
    ('demo_dex.yml', 'demo_dex', ('config', 'env', '--compose', '--internal'), None),
    ('demo_dex.yml', 'demo_dex', ('config', 'export', '--full'), None),
    ('demo_dex.yml', 'demo_dex', ('package', 'tree'), None),
    ('demo_dex.yml', 'demo_dex', ('report', 'ls'), None),
    ('demo_dex.yml', 'demo_dex', ('self', 'env'), None),
    ('demo_dex.yml', 'demo_dex', ('schema', 'export'), None),
)


@pytest.mark.parametrize(test_args, test_params)
async def test_run_init(
    config: str,
    package: str,
    cmd: str | tuple[str, ...],
    assert_fn: Callable[[], Awaitable[None]] | None,
) -> None:
    config_path = TEST_CONFIGS / config
    env_config_path = TEST_CONFIGS / 'test_sqlite.yaml'

    async with AsyncExitStack() as stack:
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                [config_path, env_config_path],
                package,
                exists=cmd != 'init',
            ),
        )
        await run_in_tmp(tmp_package_path, env, *((cmd,) if isinstance(cmd, str) else cmd))
        if not assert_fn:
            return

        await stack.enter_async_context(
            tortoise_wrapper(
                f'sqlite://{tmp_package_path}/db.sqlite3',
                f'{package}.models',
            )
        )
        await assert_fn()
