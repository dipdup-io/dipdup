from demo_events import models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TezosTzktUnknownEvent as UnknownEvent


async def on_other_event(
    ctx: HandlerContext,
    event: UnknownEvent,
) -> None:
    ...