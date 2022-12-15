from unittest import IsolatedAsyncioTestCase

import demo_factories


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_factories