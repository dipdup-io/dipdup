from contextlib import suppress
from unittest import IsolatedAsyncioTestCase

from tortoise import Tortoise

from dipdup.models import IndexType, State
from dipdup.utils import in_global_transaction, tortoise_wrapper


class UtilsTest(IsolatedAsyncioTestCase):
    async def test_in_global_transaction(self):
        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            # 1. Success query without transaction
            await State(index_name='1', index_type=IndexType.schema, hash='').save()
            count = await State.filter().count()
            self.assertEqual(1, count)

            # 2. Success query within transaction
            async with in_global_transaction():
                await State(index_name='2', index_type=IndexType.schema, hash='').save()
            count = await State.filter().count()
            self.assertEqual(2, count)

            # 3. Not rolled back query without transaction
            with suppress(Exception):
                await State(index_name='3', index_type=IndexType.schema, hash='').save()
                raise Exception
            count = await State.filter().count()
            self.assertEqual(3, count)

            # 4. Rolled back query within transaction
            with suppress(Exception):
                async with in_global_transaction():
                    await State(index_name='4', index_type=IndexType.schema, hash='').save()
                    raise Exception
            count = await State.filter().count()
            self.assertEqual(3, count)
