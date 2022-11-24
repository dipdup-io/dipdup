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

from dipdup.utils import import_submodules
from dipdup.utils.database import tortoise_wrapper


@asynccontextmanager
async def run_dipdup_demo(config: str, package: str, cmd: str = 'run') -> AsyncIterator[Path]:
    config_path = Path(__file__).parent / 'configs' / config
    dipdup_pkg_path = Path(__file__).parent.parent / 'src' / 'dipdup'
    demo_pkg_path = Path(__file__).parent.parent / 'src' / package

    with tempfile.TemporaryDirectory() as tmp_root_path:
        # NOTE: Symlink configs, packages and executables
        tmp_config_path = Path(tmp_root_path) / 'dipdup.yml'
        os.symlink(config_path, tmp_config_path)

        tmp_bin_path = Path(tmp_root_path) / 'bin'
        os.mkdir(tmp_bin_path)
        for executable in ('dipdup', 'datamodel-codegen'):
            if (executable_path := which(executable)) is None:
                raise RuntimeError(f'Executable `{executable}` not found')
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
            f'dipdup -c {tmp_config_path} {cmd}',
            cwd=tmp_root_path,
            check=True,
            shell=True,
            env=env,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        yield Path(tmp_root_path)


async def assert_run_tzbtc() -> None:
    import demo_tzbtc.models

    holders = await demo_tzbtc.models.Holder.filter().count()
    holder = await demo_tzbtc.models.Holder.first()
    assert holder
    random_balance = holder.balance

    assert holders == 4
    assert random_balance == Decimal('-0.01912431')


async def assert_run_hic_et_nunc() -> None:
    import demo_hic_et_nunc.models

    holders = await demo_hic_et_nunc.models.Holder.filter().count()
    tokens = await demo_hic_et_nunc.models.Token.filter().count()
    swaps = await demo_hic_et_nunc.models.Swap.filter().count()
    trades = await demo_hic_et_nunc.models.Trade.filter().count()

    assert holders == 22
    assert tokens == 29
    assert swaps == 20
    assert trades == 24


async def assert_run_tzcolors() -> None:
    import demo_tzcolors.models

    users = await demo_tzcolors.models.User.filter().count()
    tokens = await demo_tzcolors.models.Token.filter().count()
    auctions = await demo_tzcolors.models.Auction.filter().count()
    bids = await demo_tzcolors.models.Bid.filter().count()

    assert users == 9
    assert tokens == 14
    assert auctions == 14
    assert bids == 44


async def assert_run_tzbtc_transfers(expected_holders: int, expected_balance: str) -> None:
    import demo_tzbtc_transfers.models

    holders = await demo_tzbtc_transfers.models.Holder.filter().count()
    holder = await demo_tzbtc_transfers.models.Holder.first()
    assert holder
    random_balance = holder.balance

    assert holders == expected_holders
    assert f'{random_balance:f}' == expected_balance


async def assert_init(package: str) -> None:
    import_submodules(package)


test_args = ('config', 'package', 'cmd', 'assert_fn')
test_params = (
    ('tzbtc.yml', 'demo_tzbtc', 'run', assert_run_tzbtc),
    ('hic_et_nunc.yml', 'demo_hic_et_nunc', 'run', assert_run_hic_et_nunc),
    ('tzcolors.yml', 'demo_tzcolors', 'run', assert_run_tzcolors),
    ('tzbtc_transfers.yml', 'demo_tzbtc_transfers', 'run', partial(assert_run_tzbtc_transfers, 4, '-0.01912431')),
    ('tzbtc_transfers_2.yml', 'demo_tzbtc_transfers', 'run', partial(assert_run_tzbtc_transfers, 12, '0.26554711')),
    ('tzbtc_transfers_3.yml', 'demo_tzbtc_transfers', 'run', partial(assert_run_tzbtc_transfers, 9, '0.15579888')),
    ('tzbtc_transfers_4.yml', 'demo_tzbtc_transfers', 'run', partial(assert_run_tzbtc_transfers, 2, '-0.00767376')),
    ('domains_big_map.yml', 'demo_domains_big_map', 'init', partial(assert_init, 'demo_domains_big_map')),
    ('domains.yml', 'demo_domains', 'init', partial(assert_init, 'demo_domains')),
    ('hic_et_nunc.yml', 'demo_hic_et_nunc', 'init', partial(assert_init, 'demo_hic_et_nunc')),
    ('quipuswap.yml', 'demo_quipuswap', 'init', partial(assert_init, 'demo_quipuswap')),
    ('registrydao.yml', 'demo_registrydao', 'init', partial(assert_init, 'demo_registrydao')),
    ('tzbtc_transfers.yml', 'demo_tzbtc_transfers', 'init', partial(assert_init, 'demo_tzbtc_transfers')),
    ('tzbtc.yml', 'demo_tzbtc', 'init', partial(assert_init, 'demo_tzbtc')),
    ('tzcolors.yml', 'demo_tzcolors', 'init', partial(assert_init, 'demo_tzcolors')),
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


# @pytest.mark.skip(reason='FIXME: Huge replay')
# async def test_quipuswap() -> None:
#     async with run_dipdup_demo('quipuswap.yml', 'demo_quipuswap'):
#         trades = await demo_quipuswap.models.Trade.filter().count()
#         positions = await demo_quipuswap.models.Position.filter().count()
#         async with in_transaction() as conn:
#             symbols = (await conn.execute_query('select count(distinct(symbol)) from trade group by symbol;'))[0]
#         assert symbols == 2
#         assert trades == 835
#         assert positions == 214

# @pytest.mark.skip(reason='FIXME: Huge replay')
# async def test_domains() -> None:
#     async with run_dipdup_demo('domains.yml', 'demo_domains'):
#         tlds = await demo_domains.models.TLD.filter().count()
#         domains = await demo_domains.models.Domain.filter().count()

#         assert tlds == 1
#         assert domains == 145

# @pytest.mark.skip(reason='FIXME: Huge replay')
# async def test_domains_big_map() -> None:
#     async with run_dipdup_demo('domains_big_map.yml', 'demo_domains_big_map'):
#         tlds = await demo_domains_big_map.models.TLD.filter().count()
#         domains = await demo_domains_big_map.models.Domain.filter().count()

#         assert tlds == 1
#         assert domains == 145
