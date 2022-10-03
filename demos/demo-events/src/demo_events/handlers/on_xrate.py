
from demo_events.types.event_emitter.event.xrate import Xrate
from dipdup.models import Event
from demo_events import models as models
from dipdup.context import HandlerContext

async def on_xrate(
    ctx: HandlerContext,
    event: Event[Xrate],
) -> None:
    ...