import os
import subprocess
import tempfile
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from decimal import Decimal
from functools import partial
from pathlib import Path
from shutil import which
from typing import AsyncIterator
from typing import Awaitable
from typing import Callable

import pytest

from dipdup.database import tortoise_wrapper
from dipdup.exceptions import FrameworkException
from dipdup.models.tezos_tzkt import TzktOperationType
from dipdup.utils import import_submodules
from tests import CONFIGS_PATH
from tests import SRC_PATH


@asynccontextmanager
async def run_dipdup_demo(config: str, package: str, cmd: str = 'run') -> AsyncIterator[Path]:
    config_path = CONFIGS_PATH / config
    dipdup_pkg_path = SRC_PATH / 'dipdup'
    demo_pkg_path = SRC_PATH / package
    sqlite_config_path = Path(__file__).parent / 'configs' / 'sqlite.yaml'

    with tempfile.TemporaryDirectory() as tmp_root_path:
        # NOTE: Symlink configs, packages and executables
        tmp_config_path = Path(tmp_root_path) / 'dipdup.yaml'
        os.symlink(config_path, tmp_config_path)

        tmp_bin_path = Path(tmp_root_path) / 'bin'
        tmp_bin_path.mkdir()
        for executable in ('dipdup', 'datamodel-codegen'):
            if (executable_path := which(executable)) is None:
                raise FrameworkException(f'Executable `{executable}` not found')
            os.symlink(executable_path, tmp_bin_path / executable)

        tmp_dipdup_pkg_path = Path(tmp_root_path) / 'dipdup'
        os.symlink(dipdup_pkg_path, tmp_dipdup_pkg_path)

        # NOTE: Ensure that `run` uses existing package and `init` creates a new one
        if cmd == 'run':
            tmp_demo_pkg_path = Path(tmp_root_path) / package
            os.symlink(demo_pkg_path, tmp_demo_pkg_path)

        # NOTE: Prepare environment
        env = {
            **os.environ,
            'PATH': str(tmp_bin_path),
            'PYTHONPATH': str(tmp_root_path),
            'DIPDUP_TEST': '1',
        }

        subprocess.run(
            f'dipdup -c {tmp_config_path} -c {sqlite_config_path} {cmd}',
            cwd=tmp_root_path,
            check=True,
            shell=True,
            env=env,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        yield Path(tmp_root_path)


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


async def assert_run_big_maps() -> None:
    import demo_big_maps.models

    tlds = await demo_big_maps.models.TLD.filter().count()
    domains = await demo_big_maps.models.Domain.filter().count()

    assert tlds == 1
    assert domains == 75


async def assert_init(package: str) -> None:
    import_submodules(package)


async def assert_run_dex() -> None:
    from tortoise.transactions import in_transaction

    import demo_dex.models

    trades = await demo_dex.models.Trade.filter().count()
    positions = await demo_dex.models.Position.filter().count()
    async with in_transaction() as conn:
        symbols = (await conn.execute_query('select count(distinct(symbol)) from trade group by symbol;'))[0]
    assert symbols == 2
    assert trades == 835
    assert positions == 214


async def assert_run_domains() -> None:
    import demo_domains.models

    tlds = await demo_domains.models.TLD.filter().count()
    domains = await demo_domains.models.Domain.filter().count()

    assert tlds == 1
    assert domains == 145


async def assert_run_factories() -> None:
    import demo_factories.models

    proposals = await demo_factories.models.DAO.filter().count()
    votes = await demo_factories.models.Proposal.filter().count()

    assert proposals == 19
    assert votes == 86


async def assert_run_raw() -> None:
    import demo_raw.models

    transactions = await demo_raw.models.Operation.filter(type=TzktOperationType.transaction).count()
    originations = await demo_raw.models.Operation.filter(type=TzktOperationType.origination).count()
    migrations = await demo_raw.models.Operation.filter(type=TzktOperationType.migration).count()

    assert transactions == 167
    assert originations == 1
    assert migrations == 2


async def assert_run_dao() -> None:
    import demo_dao.models

    proposals = await demo_dao.models.DAO.filter().count()
    votes = await demo_dao.models.Proposal.filter().count()

    assert proposals == 19
    assert votes == 86


test_args = ('config', 'package', 'cmd', 'assert_fn')
test_params = (
    ('demo_token.yml', 'demo_token', 'run', assert_run_token),
    ('demo_token.yml', 'demo_token', 'init', partial(assert_init, 'demo_token')),
    ('demo_nft_marketplace.yml', 'demo_nft_marketplace', 'run', assert_run_nft_marketplace),
    ('demo_nft_marketplace.yml', 'demo_nft_marketplace', 'init', partial(assert_init, 'demo_nft_marketplace')),
    ('demo_auction.yml', 'demo_auction', 'run', assert_run_auction),
    ('demo_auction.yml', 'demo_auction', 'init', partial(assert_init, 'demo_auction')),
    ('demo_token_transfers.yml', 'demo_token_transfers', 'run', partial(assert_run_token_transfers, 4, '-0.01912431')),
    # FIXME: Why so many token transfer tests?
    ('demo_token_transfers.yml', 'demo_token_transfers', 'init', partial(assert_init, 'demo_token_transfers')),
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
    ('demo_big_maps.yml', 'demo_big_maps', 'run', assert_run_big_maps),
    ('demo_big_maps.yml', 'demo_big_maps', 'init', partial(assert_init, 'demo_big_maps')),
    ('demo_domains.yml', 'demo_domains', 'run', assert_run_domains),
    ('demo_domains.yml', 'demo_domains', 'init', partial(assert_init, 'demo_domains')),
    ('demo_dex.yml', 'demo_dex', 'run', assert_run_dex),
    ('demo_dex.yml', 'demo_dex', 'init', partial(assert_init, 'demo_dex')),
    ('demo_dao.yml', 'demo_dao', 'run', assert_run_dao),
    ('demo_dao.yml', 'demo_dao', 'init', partial(assert_init, 'demo_dao')),
    ('demo_factories.yml', 'demo_factories', 'run', assert_run_factories),
    ('demo_factories.yml', 'demo_factories', 'init', partial(assert_init, 'demo_factories')),
    ('demo_raw.yml', 'demo_raw', 'run', assert_run_raw),
    ('demo_raw.yml', 'demo_raw', 'init', partial(assert_init, 'demo_raw')),
)


@pytest.mark.parametrize(test_args, test_params)
async def test_demos(
    config: str,
    package: str,
    cmd: str,
    assert_fn: Callable[[], Awaitable[None]],
) -> None:
    async with AsyncExitStack() as stack:
        tmp_root_path = await stack.enter_async_context(
            run_dipdup_demo(config, package, cmd),
        )
        await stack.enter_async_context(
            tortoise_wrapper(
                f'sqlite://{tmp_root_path}/db.sqlite3',
                f'{package}.models',
            )
        )

        await assert_fn()
