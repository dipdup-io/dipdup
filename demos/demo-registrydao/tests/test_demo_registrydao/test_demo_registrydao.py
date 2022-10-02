from unittest import IsolatedAsyncioTestCase

import demo_registrydao


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_registrydao