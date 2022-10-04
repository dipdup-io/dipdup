import subprocess
import tempfile
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import AsyncIterator

import pytest
from tortoise.transactions import in_transaction

import demo_domains.models
import demo_domains_big_map.models
import demo_hic_et_nunc.models
import demo_quipuswap.models
import demo_tzbtc.models
import demo_tzbtc_transfers.models
import demo_tzcolors.models
from dipdup.utils.database import tortoise_wrapper


@asynccontextmanager
async def run_dipdup_demo(config: str, package: str, cmd: str = 'run') -> AsyncIterator[Path]:
    config_path = Path(__file__).parent / config
    stack = AsyncExitStack()
    async with stack:
        # NOTE: Prepare a temporary directory for each test
        tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
        Path(tmp_dir, 'dipdup.yml').write_text(config_path.read_text())

        subprocess.run(
            (
                'dipdup',
                cmd,
            ),
            cwd=tmp_dir,
            check=True,
        )
        # NOTE: Yield from opened Tortoise connection to inspect database
        await stack.enter_async_context(
            tortoise_wrapper(f'sqlite://{tmp_dir}/db.sqlite3', f'{package}.models'),
        )
        yield Path(tmp_dir)


class TestDemos:
    async def test_hic_et_nunc(self) -> None:
        async with run_dipdup_demo('hic_et_nunc.yml', 'demo_hic_et_nunc'):
            holders = await demo_hic_et_nunc.models.Holder.filter().count()
            tokens = await demo_hic_et_nunc.models.Token.filter().count()
            swaps = await demo_hic_et_nunc.models.Swap.filter().count()
            trades = await demo_hic_et_nunc.models.Trade.filter().count()

            assert holders == 22
            assert tokens == 29
            assert swaps == 20
            assert trades == 24

    async def test_quipuswap(self) -> None:
        async with run_dipdup_demo('quipuswap.yml', 'demo_quipuswap'):
            trades = await demo_quipuswap.models.Trade.filter().count()
            positions = await demo_quipuswap.models.Position.filter().count()
            async with in_transaction() as conn:
                symbols = (await conn.execute_query('select count(distinct(symbol)) from trade group by symbol;'))[0]
            assert symbols == 2
            assert trades == 835
            assert positions == 214

    async def test_tzcolors(self) -> None:
        async with run_dipdup_demo('tzcolors.yml', 'demo_tzcolors'):
            users = await demo_tzcolors.models.User.filter().count()
            tokens = await demo_tzcolors.models.Token.filter().count()
            auctions = await demo_tzcolors.models.Auction.filter().count()
            bids = await demo_tzcolors.models.Bid.filter().count()

            assert users == 9
            assert tokens == 14
            assert auctions == 14
            assert bids == 44

    async def test_domains(self) -> None:
        async with run_dipdup_demo('domains.yml', 'demo_domains'):
            tlds = await demo_domains.models.TLD.filter().count()
            domains = await demo_domains.models.Domain.filter().count()

            assert tlds == 1
            assert domains == 145

    async def test_domains_big_map(self) -> None:
        async with run_dipdup_demo('domains_big_map.yml', 'demo_domains_big_map'):
            tlds = await demo_domains_big_map.models.TLD.filter().count()
            domains = await demo_domains_big_map.models.Domain.filter().count()

            assert tlds == 1
            assert domains == 145

    async def test_tzbtc(self) -> None:
        async with run_dipdup_demo('tzbtc.yml', 'demo_tzbtc'):
            holders = await demo_tzbtc.models.Holder.filter().count()
            holder = await demo_tzbtc.models.Holder.first()
            assert holder
            random_balance = holder.balance

            assert holders == 4
            assert random_balance == Decimal('-0.01912431')

    @pytest.mark.parametrize(
        'config_file, expected_holders, expected_balance',
        [
            ('tzbtc_transfers.yml', 115, '-91396645150.66341801'),
            ('tzbtc_transfers_2.yml', 67, '-22379464893.89105268'),
            ('tzbtc_transfers_3.yml', 506, '-0.00000044'),
            ('tzbtc_transfers_4.yml', 50, '-0.00000001'),
        ],
    )
    async def test_tzbtc_transfers(self, config_file, expected_holders, expected_balance) -> None:
        async with run_dipdup_demo(config_file, 'demo_tzbtc_transfers'):
            holders = await demo_tzbtc_transfers.models.Holder.filter().count()
            holder = await demo_tzbtc_transfers.models.Holder.first()
            assert holder
            random_balance = holder.balance

            assert holders == expected_holders
            assert f'{random_balance:f}' == expected_balance


@pytest.mark.parametrize(
    'demo',
    (
        'domains_big_map',
        'domains',
        'hic_et_nunc',
        'quipuswap',
        'registrydao',
        'tzbtc_transfers',
        'tzbtc',
        'tzcolors',
    ),
)
async def test_codegen(demo: str) -> None:
    async with run_dipdup_demo(f'{demo}.yml', f'demo_{demo}', 'init'):
        ...
