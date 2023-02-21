from typing import Any
from typing import Generic
from typing import TypeVar

PayloadT = TypeVar('PayloadT', bound=Any)


class SubsquidEvent(Generic[PayloadT]):
    ...


class SubsquidOperation:
    ...
