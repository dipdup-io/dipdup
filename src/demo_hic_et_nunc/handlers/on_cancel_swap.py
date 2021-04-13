import demo_hic_et_nunc.models as models
from demo_hic_et_nunc.types.hen_minter.parameter.cancel_swap import CancelSwap
from dipdup.models import HandlerContext, OperationContext


async def on_cancel_swap(
    ctx: HandlerContext,
    cancel_swap: OperationContext[CancelSwap],
) -> None:
    swap = await models.Swap.filter(id=int(cancel_swap.parameter.__root__)).get()
    swap.status = models.SwapStatus.CANCELED
    await swap.save()
