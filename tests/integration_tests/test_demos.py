import subprocess
from os import mkdir
from os.path import dirname, join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase

import demo_hic_et_nunc.models
import demo_quipuswap.models
import demo_tzcolors.models
from dipdup.utils import tortoise_wrapper


class DemosTest(IsolatedAsyncioTestCase):
    def setUp(self):
        mkdir('/tmp/dipdup')

    def tearDown(self):
        rmtree('/tmp/dipdup')

    def run_dipdup(self, config: str):
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
            self.assertEqual(94, trades)
            self.assertEqual(56, positions)

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
