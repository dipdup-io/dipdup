from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from eth_usdt import models as models
from eth_usdt.types.eth_usdt.evm_events.transfer import Transfer


async def on_transfer(
    ctx: HandlerContext,
    event: SubsquidEvent[Transfer],
) -> None:
    print(event.payload)
