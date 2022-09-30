from unittest import IsolatedAsyncioTestCase

import demo_tzbtc


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_tzbtc