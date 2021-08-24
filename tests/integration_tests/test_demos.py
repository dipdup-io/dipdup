import subprocess
from contextlib import suppress
from os import mkdir
from os.path import dirname, join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase

from tortoise.transactions import in_transaction

import demo_hic_et_nunc.models
import demo_quipuswap.models
import demo_tezos_domains.models
import demo_tezos_domains_big_map.models
import demo_tzcolors.models
from dipdup.utils.database import tortoise_wrapper


class DemosTest(IsolatedAsyncioTestCase):
    # TODO: store cache in xdg_cache_home, keep databases and logs after last run
    def setUp(self):
        with suppress(FileNotFoundError):
            rmtree('/tmp/dipdup')
        mkdir('/tmp/dipdup')

    def run_dipdup(self, config: str):
        subprocess.run(
            [
                'dipdup',
                '-l',
                'warning.yml',
                '-c',
                join(dirname(__file__), config),
                'run',
                '--oneshot',
            ],
            cwd='/tmp/dipdup',
            check=True,
        )

    async def test_hic_et_nunc(self):
        self.run_dipdup('hic_et_nunc.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_hic_et_nunc.models'):
            holders = await demo_hic_et_nunc.models.Holder.filter().count()
            tokens = await demo_hic_et_nunc.models.Token.filter().count()
            swaps = await demo_hic_et_nunc.models.Swap.filter().count()
            trades = await demo_hic_et_nunc.models.Trade.filter().count()

            self.assertEqual(22, holders)
            self.assertEqual(29, tokens)
            self.assertEqual(20, swaps)
            self.assertEqual(24, trades)

    async def test_quipuswap(self):
        self.run_dipdup('quipuswap.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_quipuswap.models'):
            trades = await demo_quipuswap.models.Trade.filter().count()
            positions = await demo_quipuswap.models.Position.filter().count()
            async with in_transaction() as conn:
                symbols = (await conn.execute_query('select count(distinct(symbol)) from trade group by symbol;'))[0]
            self.assertEqual(2, symbols)
            self.assertEqual(835, trades)
            self.assertEqual(214, positions)

    async def test_tzcolors(self):
        self.run_dipdup('tzcolors.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tzcolors.models'):
            addresses = await demo_tzcolors.models.Address.filter().count()
            tokens = await demo_tzcolors.models.Token.filter().count()
            auctions = await demo_tzcolors.models.Auction.filter().count()
            bids = await demo_tzcolors.models.Bid.filter().count()

            self.assertEqual(9, addresses)
            self.assertEqual(14, tokens)
            self.assertEqual(14, auctions)
            self.assertEqual(44, bids)

    async def test_tezos_domains(self):
        self.run_dipdup('tezos_domains.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tezos_domains.models'):
            tlds = await demo_tezos_domains.models.TLD.filter().count()
            domains = await demo_tezos_domains.models.Domain.filter().count()

            self.assertEqual(5, tlds)
            self.assertEqual(237, domains)

    async def test_tezos_domains_big_map(self):
        self.run_dipdup('tezos_domains_big_map.yml')

        async with tortoise_wrapper('sqlite:///tmp/dipdup/db.sqlite3', 'demo_tezos_domains_big_map.models'):
            tlds = await demo_tezos_domains_big_map.models.TLD.filter().count()
            domains = await demo_tezos_domains_big_map.models.Domain.filter().count()

            self.assertEqual(5, tlds)
            self.assertEqual(237, domains)
