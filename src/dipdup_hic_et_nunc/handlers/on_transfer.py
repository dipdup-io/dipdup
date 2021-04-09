from dipdup.models import HandlerContext, OperationContext
from dipdup_hic_et_nunc.models import *
from dipdup_hic_et_nunc.types.KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton.parameter.transfer import Transfer


async def on_transfer(
    ctx: HandlerContext,
    transfer: OperationContext[Transfer],
) -> None:
    ...
