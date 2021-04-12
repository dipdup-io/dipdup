from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.transfer import Transfer


async def on_transfer(
    ctx: HandlerContext,
    transfer: OperationContext[Transfer],
) -> None:
    ...
