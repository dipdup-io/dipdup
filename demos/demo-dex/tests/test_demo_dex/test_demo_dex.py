from unittest import IsolatedAsyncioTestCase

import demo_dex


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_dex