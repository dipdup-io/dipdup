from demo_tezos_events import models as models
from demo_tezos_events.types.events_contract.tezos_events.move import MovePayload
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosEvent


async def on_move_event(
    ctx: HandlerContext,
    event: TezosEvent[MovePayload],
) -> None: ...
