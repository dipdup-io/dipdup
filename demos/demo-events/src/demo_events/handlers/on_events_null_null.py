from demo_events import models as models
from demo_events.types.events_null.event.null import NullPayload
from dipdup.context import HandlerContext
from dipdup.models import Event


async def on_events_null_null(
    ctx: HandlerContext,
    event: Event[NullPayload],
) -> None:
    ...
