from demo_events import models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktUnknownEvent


async def on_other_event(
    ctx: HandlerContext,
    event: TzktUnknownEvent,
) -> None:
    ...