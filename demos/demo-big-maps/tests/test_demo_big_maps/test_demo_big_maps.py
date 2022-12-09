from unittest import IsolatedAsyncioTestCase

import demo_big_maps


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_big_maps