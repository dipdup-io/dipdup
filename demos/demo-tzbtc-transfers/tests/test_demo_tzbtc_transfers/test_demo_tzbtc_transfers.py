from unittest import IsolatedAsyncioTestCase

import demo_tzbtc_transfers


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_tzbtc_transfers