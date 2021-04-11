from demo_hic_et_nunc.models import *
from demo_hic_et_nunc.types.hen_minter.parameter.cancel_swap import CancelSwap
from dipdup.models import HandlerContext, OperationContext


async def on_cancel_swap(
    ctx: HandlerContext,
    cancel_swap: OperationContext[CancelSwap],
) -> None:
    ...
