from unittest import IsolatedAsyncioTestCase

import demo_head


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_head