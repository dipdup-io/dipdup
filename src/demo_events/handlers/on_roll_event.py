from demo_events import models as models
from demo_events.types.events_contract.tezos_events.roll import RollPayload
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktEvent


async def on_roll_event(
    ctx: HandlerContext,
    event: TzktEvent[RollPayload],
) -> None:
    ...