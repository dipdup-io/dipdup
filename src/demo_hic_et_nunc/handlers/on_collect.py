from demo_hic_et_nunc.models import *
from demo_hic_et_nunc.types.hen_minter.parameter.collect import Collect
from dipdup.models import HandlerContext, OperationContext


async def on_collect(
    ctx: HandlerContext,
    collect: OperationContext[Collect],
) -> None:
    ...
