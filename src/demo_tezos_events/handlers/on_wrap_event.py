from demo_tezos_events import models as models
from demo_tezos_events.types.events_contract.tezos_events.wrap import WrapPayload
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosEvent


async def on_wrap_event(
    ctx: HandlerContext,
    event: TezosEvent[WrapPayload],
) -> None: ...
