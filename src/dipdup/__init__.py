from typing import (
    Any,
    Optional,
    Tuple,
    Type,
    TypeVar,
)


from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import (
    DoesNotExist,
    IntegrityError,
    TransactionManagementError,
)
from tortoise.transactions import in_transaction
from tortoise.models import Model


MODEL = TypeVar("MODEL", bound="Model")
EMPTY = object()


__version__ = '0.4.3'


async def get_or_create(
    cls: Type[MODEL],
    defaults: Optional[dict] = None,
    using_db: Optional[BaseDBAsyncClient] = None,
    **kwargs: Any,
) -> Tuple[MODEL, bool]:
    """
    Fetches the object if exists (filtering on the provided parameters),
    else creates an instance with any unspecified parameters as default values.

    :param defaults: Default values to be added to a created instance if it can't be fetched.
    :param using_db: Specific DB connection to use instead of default bound
    :param kwargs: Query parameters.
    :raises IntegrityError: If create failed
    :raises TransactionManagementError: If transaction error
    """
    if not defaults:
        defaults = {}
    db = using_db or cls._choose_db(True)
    async with in_transaction(connection_name=db.connection_name) as connection:
        try:
            return await cls.filter(**kwargs).using_db(connection).get(), False
        except DoesNotExist:
            # FIXME: tortoise-orm 0.17.4 doesn't start connection after transaction fails in `get_or_create`
            await connection.start()
            try:
                return await cls.create(using_db=connection, **defaults, **kwargs), True
            except (IntegrityError, TransactionManagementError):
                return await cls.filter(**kwargs).using_db(connection).get(), False


# FIXME: tortoise-orm 0.17.4 doesn't start connection after transaction fails in `get_or_create`
Model.get_or_create = classmethod(get_or_create)  # type: ignore
