import demo_hic_et_nunc.models as models
from demo_hic_et_nunc.types.hen_minter.parameter.cancel_swap import CancelSwapParameter
from demo_hic_et_nunc.types.hen_minter.storage import HenMinterStorage
from dipdup.context import BigMapHandlerContext, HandlerContext, OperationHandlerContext
from dipdup.models import BigMapData, BigMapDiff, OperationData, Origination, Transaction


async def on_cancel_swap(
    ctx: OperationHandlerContext,
    cancel_swap: Transaction[CancelSwapParameter, HenMinterStorage],
) -> None:
    swap = await models.Swap.filter(id=int(cancel_swap.parameter.__root__)).get()
    swap.status = models.SwapStatus.CANCELED
    await swap.save()
