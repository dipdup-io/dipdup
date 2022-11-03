from demo_events import models as models
from demo_events.types.events_tzconst.event.unit import UnitPayload
from dipdup.context import HandlerContext
from dipdup.models import Event


async def on_events_tzconst_unit(
    ctx: HandlerContext,
    event: Event[UnitPayload],
) -> None:
    ...
