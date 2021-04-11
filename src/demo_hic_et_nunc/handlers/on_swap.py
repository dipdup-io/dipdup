from demo_hic_et_nunc.models import Swap as SwapModel
from demo_hic_et_nunc.types.hen_minter.parameter.swap import Swap
from dipdup.models import HandlerContext, OperationContext


async def on_swap(
    ctx: HandlerContext,
    swap: OperationContext[Swap],
) -> None:
    ...
