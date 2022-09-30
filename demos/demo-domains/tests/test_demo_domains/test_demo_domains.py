from unittest import IsolatedAsyncioTestCase

import demo_domains


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_domains