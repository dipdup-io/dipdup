from unittest import IsolatedAsyncioTestCase

import demo_domains_big_map


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_domains_big_map