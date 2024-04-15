from demo_events import models as models
from demo_events.types.events_contract.tezos_events.roll import RollPayload
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TezosTzktEvent as Event


async def on_roll_event(
    ctx: HandlerContext,
    event: Event[RollPayload],
) -> None:
    ...