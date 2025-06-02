from dataclasses import dataclass
from typing import Any
from typing import Literal

from dipdup.subscriptions import Subscription


@dataclass(frozen=True)
class StarknetSubscription(Subscription):
    name: Literal['starknet'] = 'starknet'

    def get_params(self) -> list[Any]:
        return [self.name]
