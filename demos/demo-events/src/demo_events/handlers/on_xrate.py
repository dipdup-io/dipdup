from demo_events import models as models
from demo_events.types.event_emitter.event.xrate import XratePayload
from dipdup.context import HandlerContext
from dipdup.models import Event


async def on_xrate(
    ctx: HandlerContext,
    event: Event[XratePayload],
) -> None:
    ...
