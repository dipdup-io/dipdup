from typing import Generic
from typing import TypeVar

PayloadT = TypeVar('PayloadT', bound=None)


class SubsquidEvent(Generic[PayloadT]):
    ...


class SubsquidOperation:
    ...
