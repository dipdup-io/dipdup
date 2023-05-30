from demo_uniswap.types.position_manager.evm_events.transfer import Transfer
from demo_uniswap.utils.position import save_position_snapshot
import demo_uniswap.models as models
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def transfer(
    ctx: HandlerContext,
    event: SubsquidEvent[Transfer],
) -> None:
    position = await models.Position.get(id=event.payload.tokenId)
    position.owner = event.payload.to

    await position.save()
    await save_position_snapshot(position, event.data.level)
