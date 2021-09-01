from contextlib import suppress
from unittest import IsolatedAsyncioTestCase

from tortoise import Tortoise

from dipdup.models import Index, IndexType
from dipdup.utils.database import in_global_transaction, tortoise_wrapper


class UtilsTest(IsolatedAsyncioTestCase):
    async def test_in_global_transaction(self):
        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            # 1. Success query without transaction
            await Index(name='1', type=IndexType.operation, config_hash='').save()
            count = await Index.filter().count()
            self.assertEqual(1, count)

            # 2. Success query within transaction
            async with in_global_transaction():
                await Index(name='2', type=IndexType.operation, config_hash='').save()
            count = await Index.filter().count()
            self.assertEqual(2, count)

            # 3. Not rolled back query without transaction
            with suppress(Exception):
                await Index(name='3', type=IndexType.operation, config_hash='').save()
                raise Exception
            count = await Index.filter().count()
            self.assertEqual(3, count)

            # 4. Rolled back query within transaction
            with suppress(Exception):
                async with in_global_transaction():
                    await Index(name='4', type=IndexType.operation, config_hash='').save()
                    raise Exception
            count = await Index.filter().count()
            self.assertEqual(3, count)
