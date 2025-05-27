from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import Literal
from typing import Self
from typing import TypeVar

from pydantic import BaseModel

from dipdup.fetcher import HasLevel
from dipdup.subscriptions import Subscription

if TYPE_CHECKING:
    from starknet_py.net.client_models import EmittedEvent


@dataclass(frozen=True)
class StarknetSubscription(Subscription):
    name: Literal['starknet'] = 'starknet'

    def get_params(self) -> list[Any]:
        return [self.name]
