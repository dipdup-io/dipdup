import os
import subprocess
import tempfile
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from decimal import Decimal
from functools import partial
from pathlib import Path
from shutil import which

import pytest

from dipdup.database import get_connection
from dipdup.database import tortoise_wrapper
from dipdup.exceptions import FrameworkException
from dipdup.models.tezos_tzkt import TzktOperationType
from tests import CONFIGS_PATH
from tests import SRC_PATH


@asynccontextmanager
async def tmp_project(config_path: Path, package: str, exists: bool) -> AsyncIterator[tuple[Path, dict[str, str]]]:
    with tempfile.TemporaryDirectory() as tmp_package_path:
        # NOTE: Symlink configs, packages and executables
        tmp_config_path = Path(tmp_package_path) / 'dipdup.yaml'
        os.symlink(config_path, tmp_config_path)

        tmp_bin_path = Path(tmp_package_path) / 'bin'
        tmp_bin_path.mkdir()
        for executable in ('dipdup', 'datamodel-codegen'):
            if (executable_path := which(executable)) is None:
                raise FrameworkException(f'Executable `{executable}` not found')
            os.symlink(executable_path, tmp_bin_path / executable)

        os.symlink(
            SRC_PATH / 'dipdup',
            Path(tmp_package_path) / 'dipdup',
        )

        # NOTE: Ensure that `run` uses existing package and `init` creates a new one
        if exists:
            os.symlink(
                SRC_PATH / package,
                Path(tmp_package_path) / package,
            )

        # NOTE: Prepare environment
        env = {
            **os.environ,
            'PATH': str(tmp_bin_path),
            'PYTHONPATH': str(tmp_package_path),
            'DIPDUP_TEST': '1',
        }

        yield Path(tmp_package_path), env


async def run_in_tmp(
    tmp_path: Path,
    env: dict[str, str],
    *cmd: str,
) -> None:
    sqlite_config_path = Path(__file__).parent / 'configs' / 'sqlite.yaml'
    tmp_config_path = Path(tmp_path) / 'dipdup.yaml'

    subprocess.run(
        f'dipdup -c {tmp_config_path} -c {sqlite_config_path} {" ".join(cmd)}',
        cwd=tmp_path,
        check=True,
        shell=True,
        env=env,
        capture_output=True,
    )


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
    ('demo_events.yml', 'demo_events', 'run', assert_run_events),
    ('demo_events.yml', 'demo_events', 'init', partial(assert_init, 'demo_events')),
    ('demo_raw.yml', 'demo_raw', 'run', assert_run_raw),
    ('demo_raw.yml', 'demo_raw', 'init', partial(assert_init, 'demo_raw')),
    ('demo_evm_events.yml', 'demo_evm_events', 'run', assert_run_evm_events),
    ('demo_evm_events.yml', 'demo_evm_events', 'init', partial(assert_init, 'demo_evm_events')),
    ('demo_evm_events_node.yml', 'demo_evm_events', 'run', assert_run_evm_events),
)


@pytest.mark.parametrize(test_args, test_params)
async def test_run_init(
    config: str,
    package: str,
    cmd: str,
    assert_fn: Callable[[], Awaitable[None]],
) -> None:
    config_path = CONFIGS_PATH / config
    async with AsyncExitStack() as stack:
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                config_path,
                package,
                exists=cmd != 'init',
            ),
        )
        await run_in_tmp(tmp_package_path, env, cmd)
        await stack.enter_async_context(
            tortoise_wrapper(
                f'sqlite://{tmp_package_path}/db.sqlite3',
                f'{package}.models',
            )
        )

        await assert_fn()


async def _count_tables() -> int:
    conn = get_connection()
    _, res = await conn.execute_query('SELECT count(name) FROM sqlite_master WHERE type = "table";')
    return int(res[0][0])


async def test_schema() -> None:
    package = 'demo_token'
    config_path = CONFIGS_PATH / f'{package}.yml'

    async with AsyncExitStack() as stack:
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                config_path,
                package,
                exists=True,
            ),
        )

        def tortoise() -> AbstractAsyncContextManager[None]:
            return tortoise_wrapper(
                f'sqlite://{tmp_package_path}/db.sqlite3',
                f'{package}.models',
            )

        async with tortoise():
            conn = get_connection()
            assert (await _count_tables()) == 0

        await run_in_tmp(tmp_package_path, env, 'schema', 'init')

        async with tortoise():
            conn = get_connection()
            assert (await _count_tables()) == 10
            await conn.execute_script('CREATE TABLE test (id INTEGER PRIMARY KEY);')
            assert (await _count_tables()) == 11

        await run_in_tmp(tmp_package_path, env, 'schema', 'wipe', '--force')

        async with tortoise():
            conn = get_connection()
            assert (await _count_tables()) == 0
