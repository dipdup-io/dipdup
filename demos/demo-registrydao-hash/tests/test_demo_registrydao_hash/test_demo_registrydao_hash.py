from unittest import IsolatedAsyncioTestCase

import demo_registrydao_hash


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_registrydao_hash
