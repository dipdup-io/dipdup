from contextlib import suppress
from unittest import IsolatedAsyncioTestCase

from tortoise import Tortoise

from dipdup.enums import IndexType
from dipdup.models import Index
from dipdup.transactions import TransactionManager
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.utils.database import tortoise_wrapper


class SomeException(Exception):
    ...


class UtilsTest(IsolatedAsyncioTestCase):
    async def test_in_global_transaction(self) -> None:
        transactions = TransactionManager()
        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            # 1. Success query without transaction
            await Index(name='1', type=IndexType.operation, config_hash='').save()
            count = await Index.filter().count()
            self.assertEqual(1, count)

            # 2. Success query within transaction
            async with transactions.in_transaction():
                await Index(name='2', type=IndexType.operation, config_hash='').save()
            count = await Index.filter().count()
            self.assertEqual(2, count)

            # 3. Not rolled back query without transaction
            with suppress(SomeException):
                await Index(name='3', type=IndexType.operation, config_hash='').save()
                raise SomeException
            count = await Index.filter().count()
            self.assertEqual(3, count)

            # 4. Rolled back query within transaction
            with suppress(SomeException):
                async with transactions.in_transaction():
                    await Index(name='4', type=IndexType.operation, config_hash='').save()
                    raise SomeException
            count = await Index.filter().count()
            self.assertEqual(3, count)

    async def test_humps_helpers(self) -> None:
        self.assertEqual('foo_bar', pascal_to_snake('foo_bar', True))
        self.assertEqual('foo_bar', pascal_to_snake('FooBar', True))
        self.assertEqual('foo_bar', pascal_to_snake('Foo.Bar', True))
        self.assertEqual('foobar', pascal_to_snake('FOOBAR', True))

        self.assertEqual('foo_bar', pascal_to_snake('foo_bar', False))
        self.assertEqual('foo_bar', pascal_to_snake('FooBar', False))
        self.assertEqual('foo._bar', pascal_to_snake('Foo.Bar', False))
        self.assertEqual('foobar', pascal_to_snake('FOOBAR', False))

        self.assertEqual('FooBar', snake_to_pascal('fooBar'))
        self.assertEqual('FooBar', snake_to_pascal('FooBar'))
        self.assertEqual('Foobar', snake_to_pascal('foobar'))
        self.assertEqual('FooBar', snake_to_pascal('foo__bar'))
        self.assertEqual('Foobar', snake_to_pascal('FOOBAR'))
