from demo_events import models as models
from dipdup.context import HandlerContext
from dipdup.models import UnknownEvent


async def on_events_tzconst_unknown(
    ctx: HandlerContext,
    event: UnknownEvent,
) -> None:
    ...
