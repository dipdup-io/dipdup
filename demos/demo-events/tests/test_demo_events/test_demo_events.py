from unittest import IsolatedAsyncioTestCase

import demo_events


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_events