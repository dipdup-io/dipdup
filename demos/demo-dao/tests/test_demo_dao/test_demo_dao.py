from unittest import IsolatedAsyncioTestCase

import demo_dao


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_dao