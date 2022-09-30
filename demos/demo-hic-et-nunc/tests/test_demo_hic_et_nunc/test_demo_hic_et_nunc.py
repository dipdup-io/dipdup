from unittest import IsolatedAsyncioTestCase

import demo_hic_et_nunc


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self):
        assert demo_hic_et_nunc