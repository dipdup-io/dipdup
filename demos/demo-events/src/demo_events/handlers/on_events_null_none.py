from demo_events import models as models
from demo_events.types.events_null.event.none import NonePayload
from dipdup.context import HandlerContext
from dipdup.models import Event


async def on_events_null_none(
    ctx: HandlerContext,
    event: Event[NonePayload],
) -> None:
    ...
