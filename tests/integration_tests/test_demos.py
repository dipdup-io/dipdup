import subprocess
from contextlib import suppress
from decimal import Decimal
from os import mkdir
from os.path import dirname
from os.path import join
from shutil import rmtree

import pytest
from tortoise.transactions import in_transaction

import demo_hic_et_nunc.models
import demo_quipuswap.models
import demo_tezos_domains.models
import demo_tezos_domains_big_map.models
import demo_tzbtc.models
import demo_tzbtc_transfers.models
import demo_tzcolors.models
from dipdup.utils.database import tortoise_wrapper


class TestDemos:
    @pytest.fixture(autouse=True)
    def prepare_dir(self) -> None:
        with suppress(FileNotFoundError):
            rmtree('/tmp/dipdup')
        mkdir('/tmp/dipdup')

    def run_dipdup(self, config: str) -> None:
        subprocess.run(
            [
                'dipdup',
                '-l',
                'warning.yml',
                '-c',
                join(dirname(__file__), config),
                'run',
            ],
            cwd='/tmp/dipdup',
            check=True,
        )

    async def test_hic_et_nunc(self) -> None:
        self.run_dipdup('hic_et_nunc.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_hic_et_nunc.models'):
            holders = await demo_hic_et_nunc.models.Holder.filter().count()
            tokens = await demo_hic_et_nunc.models.Token.filter().count()
            swaps = await demo_hic_et_nunc.models.Swap.filter().count()
            trades = await demo_hic_et_nunc.models.Trade.filter().count()

            assert 22 == holders
            assert 29 == tokens
            assert 20 == swaps
            assert 24 == trades

    async def test_quipuswap(self) -> None:
        self.run_dipdup('quipuswap.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_quipuswap.models'):
            trades = await demo_quipuswap.models.Trade.filter().count()
            positions = await demo_quipuswap.models.Position.filter().count()
            async with in_transaction() as conn:
                symbols = (await conn.execute_query('select count(distinct(symbol)) from trade group by symbol;'))[0]
            assert 2 == symbols
            assert 835 == trades
            assert 214 == positions

    async def test_tzcolors(self) -> None:
        self.run_dipdup('tzcolors.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tzcolors.models'):
            addresses = await demo_tzcolors.models.Address.filter().count()
            tokens = await demo_tzcolors.models.Token.filter().count()
            auctions = await demo_tzcolors.models.Auction.filter().count()
            bids = await demo_tzcolors.models.Bid.filter().count()

            assert 9 == addresses
            assert 14 == tokens
            assert 14 == auctions
            assert 44 == bids

    async def test_tezos_domains(self) -> None:
        self.run_dipdup('tezos_domains.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tezos_domains.models'):
            tlds = await demo_tezos_domains.models.TLD.filter().count()
            domains = await demo_tezos_domains.models.Domain.filter().count()

            assert 1 == tlds
            assert 145 == domains

    async def test_tezos_domains_big_map(self) -> None:
        self.run_dipdup('tezos_domains_big_map.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tezos_domains_big_map.models'):
            tlds = await demo_tezos_domains_big_map.models.TLD.filter().count()
            domains = await demo_tezos_domains_big_map.models.Domain.filter().count()

            assert 1 == tlds
            assert 145 == domains

    async def test_tzbtc(self) -> None:
        self.run_dipdup('tzbtc.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tzbtc.models'):
            holders = await demo_tzbtc.models.Holder.filter().count()
            random_balance = (await demo_tzbtc.models.Holder.first()).balance  # type: ignore

            assert 4 == holders
            assert Decimal('-0.01912431') == random_balance

    @pytest.mark.parametrize(
        'config_file, expected_holders, expected_balance',
        [
            ('tzbtc_transfers.yml', 115, '-91396645150.66341801'),
            ('tzbtc_transfers_2.yml', 66, '-21379464893.89105268'),
            ('tzbtc_transfers_3.yml', 502, '-0.00000043'),
            ('tzbtc_transfers_4.yml', 32, '-0.00000001'),
        ],
    )
    async def test_tzbtc_transfers(self, config_file, expected_holders, expected_balance) -> None:
        self.run_dipdup(config_file)

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tzbtc_transfers.models'):
            holders = await demo_tzbtc_transfers.models.Holder.filter().count()
            random_balance = (await demo_tzbtc_transfers.models.Holder.first()).balance  # type: ignore

            assert holders == expected_holders
            assert f'{random_balance:f}' == expected_balance
