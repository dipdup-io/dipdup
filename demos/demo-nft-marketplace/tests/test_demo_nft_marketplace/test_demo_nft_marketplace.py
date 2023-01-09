from unittest import IsolatedAsyncioTestCase

import demo_nft_marketplace


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_nft_marketplace