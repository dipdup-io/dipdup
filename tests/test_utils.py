from contextlib import suppress

from pytest import raises
from tortoise import Tortoise

from dipdup.database import iter_models
from dipdup.database import tortoise_wrapper
from dipdup.exceptions import FrameworkException
from dipdup.models import Index
from dipdup.models import IndexType
from dipdup.transactions import TransactionManager
from dipdup.utils import import_submodules
from dipdup.utils import parse_object
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from tests.types.kolibri_ovens.set_delegate import SetDelegateParameter
from tests.types.qwer.storage import QwerStorage
from tests.types.qwer.storage import QwerStorageItem1


class SomeException(Exception): ...


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


async def test_import_submodules() -> None:
    with raises(FrameworkException):
        import_submodules('demo_token')

    submodules = import_submodules('demo_token.handlers')
    assert len(submodules) == 3


async def test_parse_object() -> None:
    # empty
    empty = parse_object(SetDelegateParameter, None)
    assert empty.__root__ is None
    # string only
    str_ = parse_object(SetDelegateParameter, 'some')
    assert str_.__root__ == 'some'
    # map
    map_ = parse_object(QwerStorage, [[{'R': {'a': 'b'}}, {'R': {}}], [{'L': 'test'}]])
    assert isinstance(map_.__root__[0][0], QwerStorageItem1)
    assert map_.__root__[0][0].R['a'] == 'b'
