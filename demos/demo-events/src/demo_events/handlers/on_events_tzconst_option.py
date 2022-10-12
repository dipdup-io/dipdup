from demo_events import models as models
from demo_events.types.events_tzconst.event.option import OptionPayload
from dipdup.context import HandlerContext
from dipdup.models import Event


async def on_events_tzconst_option(
    ctx: HandlerContext,
    event: Event[OptionPayload],
) -> None:
    ...
