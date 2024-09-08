from demo_tezos_events import models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosUnknownEvent


async def on_other_event(
    ctx: HandlerContext,
    event: TezosUnknownEvent,
) -> None: ...
