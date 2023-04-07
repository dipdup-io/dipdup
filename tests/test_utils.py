from contextlib import suppress

from tortoise import Tortoise

from dipdup.database import iter_models
from dipdup.database import tortoise_wrapper
from dipdup.models import Index
from dipdup.models import IndexType
from dipdup.transactions import TransactionManager
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


class SomeException(Exception):
    ...


async def test_in_global_transaction() -> None:
    transactions = TransactionManager()
    async with tortoise_wrapper('sqlite://:memory:'):
        await Tortoise.generate_schemas()

        # 1. Success query without transaction
        await Index(name='1', type=IndexType.tezos_tzkt_operations, config_hash='').save()
        count = await Index.filter().count()
        assert count == 1

        # 2. Success query within transaction
        async with transactions.in_transaction():
            await Index(name='2', type=IndexType.tezos_tzkt_operations, config_hash='').save()
        count = await Index.filter().count()
        assert count == 2

        # 3. Not rolled back query without transaction
        with suppress(SomeException):
            await Index(name='3', type=IndexType.tezos_tzkt_operations, config_hash='').save()
            raise SomeException
        count = await Index.filter().count()
        assert count == 3

        # 4. Rolled back query within transaction
        with suppress(SomeException):
            async with transactions.in_transaction():
                await Index(name='4', type=IndexType.tezos_tzkt_operations, config_hash='').save()
                raise SomeException
        count = await Index.filter().count()
        assert count == 3


async def test_humps_helpers() -> None:
    assert pascal_to_snake('foo_bar', True) == 'foo_bar'
    assert pascal_to_snake('FooBar', True) == 'foo_bar'
    assert pascal_to_snake('Foo.Bar', True) == 'foo_bar'
    assert pascal_to_snake('FOOBAR', True) == 'foobar'

    assert pascal_to_snake('foo_bar', False) == 'foo_bar'
    assert pascal_to_snake('FooBar', False) == 'foo_bar'
    assert pascal_to_snake('Foo.Bar', False) == 'foo._bar'
    assert pascal_to_snake('FOOBAR', False) == 'foobar'

    assert snake_to_pascal('fooBar') == 'FooBar'
    assert snake_to_pascal('FooBar') == 'FooBar'
    assert snake_to_pascal('foobar') == 'Foobar'
    assert snake_to_pascal('foo__bar') == 'FooBar'
    assert snake_to_pascal('FOOBAR') == 'Foobar'


async def test_iter_models() -> None:
    models = list(iter_models('demo_token'))
    assert len(models) == 9
    assert models[0][0] == 'int_models'
    assert models[-1][0] == 'models'
