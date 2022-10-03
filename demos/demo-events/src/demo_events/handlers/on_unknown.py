
from dipdup.models import UnknownEvent
from demo_events import models as models
from dipdup.context import HandlerContext

async def on_unknown(
    ctx: HandlerContext,
    event: UnknownEvent,
) -> None:
    ...