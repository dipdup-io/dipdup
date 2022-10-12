from demo_events import models as models
from demo_events.types.events.event.xrate import XratePayload
from dipdup.context import HandlerContext
from dipdup.models import Event


async def on_events_xrate(
    ctx: HandlerContext,
    event: Event[XratePayload],
) -> None:
    ...
