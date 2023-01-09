from unittest import IsolatedAsyncioTestCase

import demo_token_transfers


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_token_transfers