from dipdup.models import HandlerContext, OperationContext

import demo_tzcolors.models as models

from demo_tzcolors.types.tzcolors_minter.parameter.initial_auction import InitialAuction
from demo_tzcolors.types.tzcolors_auction.parameter.create_auction import CreateAuction


async def on_initial_auction(
    ctx: HandlerContext,
    initial_auction: OperationContext[InitialAuction],
    create_auction: OperationContext[CreateAuction],
) -> None:
    ...