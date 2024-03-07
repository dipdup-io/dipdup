from demo_events import models as models
from demo_events.types.events_contract.event.move import MovePayload
from dipdup.context import HandlerContext
from dipdup.models import Event


async def on_move_event(
    ctx: HandlerContext,
    event: Event[MovePayload],
) -> None: ...
